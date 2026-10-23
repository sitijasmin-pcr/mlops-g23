from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .schemas import ChatRequest
from .workers import BY_ID, public_workers
from .lmstudio import models, stream_chat

app = FastAPI(title='PCR Kantor AI')
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=['GET','POST'], allow_headers=['Content-Type'])

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'detail':'Pesan tidak valid. Maksimal 4000 karakter per pesan pengguna, 30 pesan, 60000 karakter riwayat, 4 gambar per pesan, 5 MB per gambar, dan 20 MB gambar per riwayat.'})

@app.get('/api/health')
async def health():
    try:
        available = await models()
        ready = settings.lm_studio_model in available
    except Exception:
        ready = False
    return {'status':'ok', 'lm_studio':ready, 'model':settings.lm_studio_model}

@app.get('/api/workers')
async def workers():
    return public_workers()

@app.post('/api/chat')
async def chat(body: ChatRequest):
    worker = BY_ID.get(body.worker_id)
    if not worker:
        raise HTTPException(404, 'Pekerja tidak ditemukan.')
    return StreamingResponse(stream_chat(worker, body.messages), media_type='text/event-stream', headers={'Cache-Control':'no-cache', 'X-Accel-Buffering':'no'})

dist = Path(__file__).resolve().parents[1] / 'frontend/dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
