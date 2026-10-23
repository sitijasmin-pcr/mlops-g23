# PCR — Kantor AI 3D

Simulasi software house dengan gedung 3D terinspirasi foto PCR

## Arsitektur

Browser (Three.js + Vite) → /api FastAPI → LM Studio lokal → Qwen. Jawaban dikirim melalui Server-Sent Events dalam respons POST dan dibaca Fetch streaming. Tidak memakai API OpenAI. Semua URL dan nama model ada di backend; frontend tidak mengakses LM Studio langsung.

Data kelima pekerja, warna, posisi, deskripsi dan prompt dikelola dalam satu file shared/workers.json. Endpoint pekerja tidak mengirim prompt sistem. Riwayat chat disimpan dalam memori browser per pekerja dan hilang ketika halaman dimuat ulang.

## Struktur folder

```text
pcr-kantor-ai/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── style.css
│       ├── api.js
│       ├── config/workers.js
│       ├── scene/
│       │   ├── office.js
│       │   ├── worker.js
│       │   ├── camera.js
│       │   └── interactions.js
│       └── ui/chat-panel.js
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── workers.py
│   ├── lmstudio.py
│   ├── test_api.py
│   ├── requirements.txt
│   └── .env.example
├── shared/workers.json
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── README.md
```

## 1. Persiapan

Pasang Python 3.11 atau lebih baru dari python.org (aktifkan Add Python to PATH), Node.js 22 LTS atau versi yang kompatibel dari nodejs.org, serta LM Studio dari lmstudio.ai. Docker Desktop hanya diperlukan untuk cara Docker; aktifkan mesin Linux/WSL2 pada Windows. Periksa python --version, node --version dan npm --version. Di Linux, gunakan python3 dan pasang paket python3-venv bila belum tersedia.

## 2. Menyiapkan Qwen

Buka LM Studio, cari model percakapan Qwen dalam format GGUF yang sesuai RAM/VRAM, unduh, lalu muat model tersebut. Buka halaman Developer / Local Server dan aktifkan server pada port 1234. Salin identifier model persis seperti yang dilaporkan GET /v1/models, misalnya identifier model yang Anda unduh; nilai qwen di contoh hanyalah default konfigurasi dan harus cocok dengan model yang dimuat.

Jangan mengekspos port 1234 ke internet. Aplikasi ini diasumsikan untuk satu pengguna lokal dan tidak memiliki autentikasi publik.

## 3. Menjalankan lokal — Windows PowerShell

Buka terminal di folder proyek.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
notepad backend/.env
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Atur LM_STUDIO_MODEL sesuai identifier model yang dimuat. LM_STUDIO_URL default adalah http://127.0.0.1:1234/v1.

Buka terminal kedua di folder proyek:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Buka http://127.0.0.1:5173. Vite meneruskan /api ke FastAPI port 8000. Cara ini tidak memerlukan aktivasi PowerShell virtual environment.

## 4. Linux / WSL

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env, terutama LM_STUDIO_MODEL.
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Terminal kedua:
cd frontend
npm ci
npm run dev
```

Jika LM Studio ada di Windows sedangkan backend di WSL, localhost dapat berbeda tergantung mode jaringan WSL. Gunakan alamat host Windows yang dapat dijangkau pada LM_STUDIO_URL atau jalankan kedua proses di Windows.

## 5. Produksi lokal / satu server

Jalankan npm run build dari folder frontend, lalu jalankan Uvicorn seperti di atas. FastAPI menyajikan frontend/dist jika sudah ada saat proses dimulai. Buka http://127.0.0.1:8000. Tidak perlu server Vite setelah build.

## 6. Docker Compose

Salin .env.example di akar proyek menjadi .env (PowerShell: Copy-Item .env.example .env; Linux: cp .env.example .env). Atur identifier LM_STUDIO_MODEL di .env akar untuk Compose. backend/.env dipakai untuk proses lokal dan dikecualikan dari image.

```bash
docker compose up --build
```

Buka http://localhost:8000. Container menyajikan frontend dan FastAPI sekaligus. LM Studio tetap di host, diakses melalui http://host.docker.internal:1234/v1. extra_hosts sudah disertakan untuk host gateway Linux. Jika server LM Studio hanya menerima loopback, aktifkan akses jaringan lokal pada LM Studio dan batasi firewall ke jaringan Docker yang diperlukan. Jangan membuka port ke internet. Hentikan dengan Ctrl+C atau docker compose down.

## 7. Cara menggunakan

- Tab Gedung menampilkan eksterior. Tab Ruang kerja atau tombol Masuk menampilkan kantor.
- Tarik pointer untuk orbit, gulir untuk zoom, gunakan tombol +, −, atau rumah untuk reset.
- Klik karakter, label nama, atau kartu pekerja di kiri untuk memusatkan kamera dan membuka chat.
- Rina membantu proposal; Melati keuangan; Arief pengembangan; Dewi media sosial; Hendra pengujian web.
- Enter mengirim pesan; Shift+Enter membuat baris baru. Maksimal pesan pengguna 4000 karakter.
- Gunakan tombol **＋ Gambar** untuk melampirkan PNG, JPEG, atau WEBP ke chat VLM. Maksimal 4 gambar per pesan dan 5 MB per gambar; model yang dimuat di LM Studio harus mendukung input gambar.
- Jawaban muncul bertahap, tangan/kepala bergerak saat berpikir, status berubah ketika selesai.
- Pindah pekerja tanpa kehilangan chat selama sesi. Pengiriman paralel ke pekerja lain didukung; LM Studio dapat mengantrekannya.
- Hapus chat mengosongkan riwayat pekerja aktif. Tidak tersedia saat respons sedang berlangsung.
- Tombol status kanan atas memeriksa koneksi; pemeriksaan otomatis setiap 30 detik.

## 8. API dan batasan

GET /api/health mengembalikan status backend, kesiapan identifier model dan nama model. GET /api/workers mengembalikan data visual lima pekerja. POST /api/chat menerima worker_id dan messages dengan role user/assistant. Pesan pengguna dapat berisi teks dan lampiran gambar dalam format OpenAI-compatible `image_url` data URL (PNG/JPEG/WEBP). Maksimal 4 gambar per pesan, 5 MB per gambar, 20 MB gambar per riwayat, 30 pesan, 60000 karakter total, dan 12000 karakter per pesan assistant. Prompt sistem ditambahkan di server. Streaming memakai data JSON dengan type token/content, done, atau error/message. Timeout koneksi 5 detik dan baca respons 90 detik. API docs tersedia di /docs.

## 9. Pengujian

Dari akar proyek: .venv\Scripts\python.exe -m pytest backend/test_api.py -q (Linux: .venv/bin/python -m pytest backend/test_api.py -q). Uji otomatis memakai transport LM Studio tiruan, bukan respons Qwen asli, untuk memeriksa validasi, privasi prompt, streaming, kegagalan koneksi, koneksi terputus, kesehatan model dan CORS.

Uji akhir dengan LM Studio nyata:

1. Pastikan /api/health menunjukkan lm_studio: true.
2. Buka tiap pekerja dan kirim pertanyaan sesuai perannya; pastikan jawaban bertambah bertahap.
3. Pindah pekerja saat jawaban berlangsung dan kembali; riwayat harus tetap terpisah.
4. Putar/zoom kamera, pilih karakter dan label, lalu reset tampilan.
5. Matikan LM Studio; chat harus menunjukkan pesan kegagalan yang jelas.
6. Matikan FastAPI saat Vite masih hidup; kirim pesan dan periksa pesan backend.
7. Uji pada layar kecil dan pastikan tombol serta chat bisa dipakai.
8. Bangun Docker, buka localhost:8000, dan ulangi percakapan.

## 10. Pemecahan masalah

**Backend belum berjalan. Jalankan FastAPI terlebih dahulu.** Jalankan Uvicorn dari akar proyek pada port 8000. Jika daftar pekerja belum terisi, muat ulang halaman setelah backend aktif.

**LM Studio belum aktif atau model Qwen belum dimuat.** Aktifkan server, muat model, cocokkan identifier pada LM_STUDIO_MODEL, lalu mulai ulang backend. Tombol status memeriksa identifier persis, bukan sekadar nama keluarga Qwen.

**CORS:** gunakan alamat frontend yang ditentukan FRONTEND_ORIGIN. Proxy Vite dan produksi satu origin tidak perlu akses lintas origin. Jika alamat frontend diubah, ubah konfigurasi backend lalu mulai ulang.

**Port terpakai:** hentikan proses lama atau ubah port Uvicorn beserta target proxy di vite.config.js. Port Vite memakai strictPort agar tidak diam-diam bergeser.

**Model lambat / timeout:** gunakan quantization atau model lebih kecil, pendekkan prompt, turunkan MAX_TOKENS, periksa memori GPU/RAM.

**WebGL:** aktifkan akselerasi perangkat keras dan gunakan browser modern. Bayangan 2048 piksel dan rasio piksel dibatasi 1.75; turunkan pengaturan renderer jika laptop berat. Tidak ada model 3D eksternal atau font jaringan yang diperlukan setelah dependency terpasang.

**Respons terpotong:** riwayat yang diterima sebagian tetap terlihat. Jawaban parsial bukan hasil lengkap; kirim permintaan lanjutan atau hapus percakapan.

Tes parser streaming frontend: jalankan node --test src/api.test.js dari folder frontend.
