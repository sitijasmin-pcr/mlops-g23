
import os
import io
import json
import base64
import re
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field


load_dotenv()

app = FastAPI(title="Receipt Finance API", version="1.0.0")

# CORS untuk frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Koneksi ke LM Studio
client = AsyncOpenAI(
    base_url=os.getenv(
        "MODEL_BASE_URL",
        "http://host.docker.internal:1234/v1",
    ),
    api_key=os.getenv("MODEL_API_KEY", "lm-studio"),
    timeout=120.0,
)

MODEL_NAME = os.getenv("MODEL_NAME", "").strip()
MAX_BYTES = int(os.getenv("MAX_FILE_MB", "8")) * 1024 * 1024


# Model data nota
class ReceiptItem(BaseModel):
    name: str
    quantity: Optional[float] = 1.0
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None


class ReceiptData(BaseModel):
    merchant: Optional[str] = None
    transaction_date: Optional[str] = None
    currency: Optional[str] = "IDR"
    items: list[ReceiptItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[str] = None


class ReceiptResponse(BaseModel):
    success: bool
    data: ReceiptData
    metadata: dict


# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}


# Membersihkan angka seperti Rp 70.000 atau 12,500
def clean_number(value):
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        return None

    cleaned = re.sub(r"[^\d.,-]", "", value.strip())

    if not cleaned or cleaned in {"-", ".", ","}:
        return None

    if "." in cleaned and "," in cleaned:
        # Pemisah terakhir dianggap desimal
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    elif "." in cleaned or "," in cleaned:
        separator = "." if "." in cleaned else ","
        parts = cleaned.split(separator)

        if len(parts) > 2:
            cleaned = "".join(parts)
        elif len(parts) == 2:
            if len(parts[-1]) == 3:
                cleaned = "".join(parts)
            elif separator == ",":
                cleaned = ".".join(parts)

    try:
        return float(cleaned)
    except ValueError:
        return None


# Endpoint ekstraksi nota
@app.post(
    "/api/receipts/extract",
    response_model=ReceiptResponse,
)
async def extract_receipt(file: UploadFile = File(...)):
    try:
        if not MODEL_NAME:
            raise HTTPException(
                status_code=500,
                detail="MODEL_NAME belum dikonfigurasi",
            )

        # Validasi tipe file
        if file.content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise HTTPException(
                status_code=415,
                detail="Format gambar tidak didukung",
            )

        # Validasi ukuran file
        raw = await file.read(MAX_BYTES + 1)

        if not raw:
            raise HTTPException(
                status_code=400,
                detail="Gambar kosong",
            )

        if len(raw) > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Gambar melebihi batas ukuran",
            )

        # Validasi gambar
        try:
            image = Image.open(io.BytesIO(raw))
            image.verify()

            image = Image.open(io.BytesIO(raw))
            image_format = image.format

            if image_format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(
                    status_code=415,
                    detail="Format gambar tidak didukung",
                )

        except (UnidentifiedImageError, OSError):
            raise HTTPException(
                status_code=400,
                detail="Berkas bukan gambar yang valid",
            )

        mime_types = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }

        mime = mime_types[image_format]
        encoded = base64.b64encode(raw).decode("ascii")
        image_url = f"data:{mime};base64,{encoded}"

        # Instruksi untuk model vision
        prompt = """
Ekstrak informasi nota keuangan dari gambar.

Kembalikan tepat satu objek JSON valid.
Jangan gunakan Markdown, code fence, komentar, atau teks tambahan.

Gunakan struktur berikut:
{
  "merchant": null,
  "transaction_date": null,
  "currency": "IDR",
  "items": [
    {
      "name": "nama barang",
      "quantity": 1,
      "unit_price": 10000,
      "subtotal": 10000
    }
  ],
  "subtotal": null,
  "tax": null,
  "discount": null,
  "total": null,
  "payment_method": null
}

Ketentuan:
- Gunakan tanda kutip ganda untuk nama properti dan string.
- Semua nilai uang dan quantity harus berupa angka JSON atau null.
- Jangan sertakan simbol Rp, titik ribuan, atau teks satuan dalam angka.
- Tanggal gunakan format YYYY-MM-DD atau null.
- Jika data tidak terlihat atau tidak diketahui, gunakan null.
- Jangan mengarang data yang tidak terlihat.
- Gunakan [] jika tidak ada barang yang dapat dikenali.
- Pastikan koma, kurung, dan tanda kutip JSON benar.
"""

        # Panggil model LM Studio
        try:
            result = await client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                },
                            },
                        ],
                    }
                ],
            )

            content = result.choices[0].message.content

            if not content:
                raise ValueError("Output model kosong")

            # Ambil objek JSON dari respons model
            start = content.find("{")
            end = content.rfind("}")

            if start < 0 or end < start:
                raise ValueError("JSON tidak ditemukan dalam respons model")

            json_text = content[start:end + 1]

            try:
                payload = json.loads(json_text)
            except json.JSONDecodeError as error:
                print(
                    f"JSON MODEL TIDAK VALID: {error}",
                    flush=True,
                )
                print(
                    f"RESPONS MODEL:\n{content}",
                    flush=True,
                )
                raise ValueError(
                    "Model menghasilkan JSON yang tidak valid"
                ) from error

            if not isinstance(payload, dict):
                raise ValueError("Respons model bukan objek JSON")

            # Normalisasi data nota
            payload.setdefault("currency", "IDR")

            for key in ("subtotal", "tax", "discount", "total"):
                if key in payload:
                    payload[key] = clean_number(payload[key])

            items = payload.get("items", [])

            if not isinstance(items, list):
                items = []

            cleaned_items = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                name = item.get("name")

                if not isinstance(name, str) or not name.strip():
                    continue

                quantity = clean_number(item.get("quantity"))

                cleaned_items.append(
                    {
                        "name": name.strip(),
                        "quantity": (
                            1.0 if quantity is None else quantity
                        ),
                        "unit_price": clean_number(
                            item.get("unit_price")
                        ),
                        "subtotal": clean_number(
                            item.get("subtotal")
                        ),
                    }
                )

            payload["items"] = cleaned_items

            # Validasi hasil akhir
            data = ReceiptData.model_validate(payload)

            return ReceiptResponse(
                success=True,
                data=data,
                metadata={
                    "model": MODEL_NAME,
                    "processing_status": "success",
                },
            )

        except HTTPException:
            raise

        except Exception as error:
            print(
                f"ERROR INFERENSI NOTA: {error!r}",
                flush=True,
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "Inferensi gagal atau output model tidak valid"
                ),
            ) from error

    finally:
        await file.close()


# Model request untuk AI Chat
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


# Endpoint AI Chat menggunakan LM Studio
@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not MODEL_NAME:
        raise HTTPException(
            status_code=500,
            detail="MODEL_NAME belum dikonfigurasi",
        )

    if not request.messages:
        raise HTTPException(
            status_code=400,
            detail="Pesan tidak boleh kosong",
        )

    allowed_roles = {"user", "assistant"}

    for message in request.messages:
        if message.role not in allowed_roles:
            raise HTTPException(
                status_code=400,
                detail="Role pesan tidak valid",
            )

        if not message.content.strip():
            raise HTTPException(
                status_code=400,
                detail="Isi pesan tidak boleh kosong",
            )

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Kamu adalah AI Assistant yang ramah. "
                        "Jawab pertanyaan pengguna dengan jelas, "
                        "membantu, dan gunakan bahasa yang sesuai "
                        "dengan bahasa pengguna."
                    ),
                },
                *[
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in request.messages
                ],
            ],
            temperature=0.7,
        )

        answer = response.choices[0].message.content

        return {
            "success": True,
            "reply": answer or "Maaf, model tidak memberikan jawaban.",
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(f"AI Chat error: {type(exc).__name__}: {exc}")

        raise HTTPException(
            status_code=502,
            detail=(
                "Gagal mendapatkan jawaban dari LM Studio. "
                "Pastikan LM Studio aktif dan model sudah dimuat."
            ),
        )
