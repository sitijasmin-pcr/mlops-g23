import base64
import binascii
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_HISTORY_IMAGE_BYTES = 20 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/png', 'image/jpeg', 'image/webp'}
IMAGE_DATA_URL = re.compile(r'^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/]+={0,2})$')


class TextPart(BaseModel):
    type: Literal['text']
    text: str = Field(min_length=1, max_length=4000)

    @field_validator('text')
    @classmethod
    def valid_text(cls, value):
        if not value.strip():
            raise ValueError('Pesan tidak boleh kosong.')
        return value


class ImageUrl(BaseModel):
    url: str = Field(min_length=1, max_length=7 * 1024 * 1024)

    @field_validator('url')
    @classmethod
    def valid_image_url(cls, value):
        match = IMAGE_DATA_URL.fullmatch(value)
        if not match or match.group(1) not in ALLOWED_IMAGE_TYPES:
            raise ValueError('Gambar harus berupa data URL PNG, JPEG, atau WEBP.')
        try:
            image = base64.b64decode(match.group(2), validate=True)
        except binascii.Error as error:
            raise ValueError('Data gambar tidak valid.') from error
        if not image or len(image) > MAX_IMAGE_BYTES:
            raise ValueError('Ukuran gambar maksimal 5 MB.')
        image_type = match.group(1)
        if image_type == 'image/png' and not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Isi gambar tidak sesuai dengan format PNG.')
        if image_type == 'image/jpeg' and not image.startswith(b'\xff\xd8\xff'):
            raise ValueError('Isi gambar tidak sesuai dengan format JPEG.')
        if image_type == 'image/webp' and not (image.startswith(b'RIFF') and image[8:12] == b'WEBP'):
            raise ValueError('Isi gambar tidak sesuai dengan format WEBP.')
        return value

    @property
    def decoded_size(self):
        return len(base64.b64decode(self.url.partition(',')[2]))


class ImagePart(BaseModel):
    type: Literal['image_url']
    image_url: ImageUrl


class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str | list[TextPart | ImagePart] = Field(max_length=12000)

    @field_validator('content')
    @classmethod
    def valid_content(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError('Pesan tidak boleh kosong.')
        return value

    @model_validator(mode='after')
    def valid_parts(self):
        if isinstance(self.content, list):
            if self.role != 'user':
                raise ValueError('Lampiran gambar hanya boleh dikirim oleh pengguna.')
            text_parts = [part for part in self.content if isinstance(part, TextPart)]
            image_parts = [part for part in self.content if isinstance(part, ImagePart)]
            if not image_parts or len(text_parts) > 1 or len(image_parts) > 4:
                raise ValueError('Pesan harus berisi 1-4 gambar dan maksimal satu bagian teks.')
        return self


class ChatRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=40)
    messages: list[Message] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def valid_history(self):
        if self.messages[-1].role != 'user':
            raise ValueError('Pesan terakhir harus dari pengguna.')
        total_text = 0
        total_image_bytes = 0
        for message in self.messages:
            if isinstance(message.content, str):
                content_length = len(message.content)
                if message.role == 'user' and content_length > 4000:
                    raise ValueError('Pesan pengguna maksimal 4000 karakter.')
                total_text += content_length
            else:
                for part in message.content:
                    if isinstance(part, TextPart):
                        total_text += len(part.text)
                    else:
                        total_image_bytes += part.image_url.decoded_size
        if total_text > 60000:
            raise ValueError('Riwayat terlalu panjang.')
        if total_image_bytes > MAX_HISTORY_IMAGE_BYTES:
            raise ValueError('Total gambar dalam riwayat maksimal 20 MB.')
        return self
