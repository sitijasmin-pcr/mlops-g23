# Hasil pengujian

- Build Vite berhasil; bundle JavaScript sekitar 516 kB (132 kB gzip).
- 7 tes backend lulus: daftar pekerja tanpa prompt sistem, validasi input, streaming dan prompt pekerja, kegagalan koneksi, status model, aliran terputus, dan CORS.
- FastAPI menyajikan aplikasi produksi dengan HTTP 200.
- Pratinjau browser menampilkan gedung Three.js dan pemilihan Arief membuka interior serta panel chat.
- LM Studio belum tersedia dengan identifier model yang dikonfigurasi; respons Qwen asli belum diverifikasi.
- Docker tidak tersedia di lingkungan pengujian; konfigurasi disertakan, tetapi build container belum dijalankan.

Tes otomatis streaming menggunakan MockTransport HTTPX. Panduan uji Qwen sebenarnya dan Docker tersedia dalam README.md.

- 2 tes frontend lulus: token UTF-8 lintas chunk dan deteksi aliran tanpa penanda selesai.
- Browser memverifikasi error LM Studio saat mengirim pesan, serta tampilan interior berisi kelima karakter.
