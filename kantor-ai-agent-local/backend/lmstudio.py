import json
import httpx
from .config import settings

UNAVAILABLE = 'LM Studio belum aktif atau model Qwen belum dimuat.'
def event(data):
    return 'data: ' + json.dumps(data, ensure_ascii=False) + '\n\n'

async def models():
    async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
        response = await client.get(settings.lm_studio_url.rstrip('/') + '/models')
        response.raise_for_status()
        return [m['id'] for m in response.json().get('data', [])]

async def stream_chat(worker, messages):
    payload = {
        'model': settings.lm_studio_model, 'stream': True,
        'temperature': settings.temperature, 'max_tokens': settings.max_tokens,
        'messages': [{'role':'system', 'content': f"Anda adalah {worker['name']}, {worker['role']} di PCR Software House. Gunakan bahasa Indonesia yang jelas. {worker['system']}"}] + [m.model_dump() for m in messages]
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=5.0), trust_env=False) as client:
            async with client.stream('POST', settings.lm_studio_url.rstrip('/') + '/chat/completions', json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    value = line[5:].strip()
                    if value == '[DONE]':
                        yield event({'type':'done'})
                        return
                    data = json.loads(value)
                    if data.get('error'):
                        yield event({'type':'error', 'message':UNAVAILABLE})
                        return
                    for choice in data.get('choices', []):
                        token = choice.get('delta', {}).get('content')
                        if token:
                            yield event({'type':'token', 'content':token})
                        if choice.get('finish_reason'):
                            yield event({'type':'done'})
                            return
                yield event({'type':'error', 'message':'Koneksi model terputus sebelum jawaban selesai.'})
    except httpx.TimeoutException:
        yield event({'type':'error', 'message':'Model terlalu lama merespons. Coba pesan yang lebih singkat.'})
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        yield event({'type':'error', 'message':UNAVAILABLE})
