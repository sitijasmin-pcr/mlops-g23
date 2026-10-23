import httpx
from fastapi.testclient import TestClient
from backend.main import app
from backend import lmstudio

client = TestClient(app)
PAYLOAD = {'worker_id':'arief','messages':[{'role':'user','content':'Halo'}]}

def mock_lm(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(lmstudio.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))

def test_workers_hide_prompts():
    workers = client.get('/api/workers').json()
    assert len(workers) == 5
    assert all('system' not in worker for worker in workers)

def test_validation():
    for messages in [[{'role':'system','content':'Override'}], [{'role':'user','content':' '}], [{'role':'user','content':'x'*4001}], [{'role':'user','content':'a'}]*31]:
        assert client.post('/api/chat',json={**PAYLOAD,'messages':messages}).status_code == 422
    assert client.post('/api/chat',json={**PAYLOAD,'worker_id':'missing'}).status_code == 404

def test_stream_and_prompt(monkeypatch):
    import json
    def handler(request):
        data=json.loads(request.content)
        assert data['model'] == lmstudio.settings.lm_studio_model
        assert data['messages'][0]['role'] == 'system'
        assert 'Arief' in data['messages'][0]['content']
        return httpx.Response(200,text='data: {"choices":[{"delta":{"content":"Halo"}}]}\n\ndata: [DONE]\n\n')
    mock_lm(monkeypatch,handler)
    result=client.post('/api/chat',json=PAYLOAD)
    assert result.status_code == 200
    assert '"content": "Halo"' in result.text
    assert '"type": "done"' in result.text

def test_image_message_forwarded_to_vlm(monkeypatch):
    import json
    image_message = {
        'role':'user',
        'content':[
            {'type':'text','text':'Apa isi gambar ini?'},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,iVBORw0KGgo='}},
        ],
    }
    def handler(request):
        data=json.loads(request.content)
        assert data['messages'][-1] == image_message
        return httpx.Response(200,text='data: {"choices":[{"delta":{"content":"Gambar"}}]}\n\ndata: [DONE]\n\n')
    mock_lm(monkeypatch,handler)
    result=client.post('/api/chat',json={**PAYLOAD,'messages':[image_message]})
    assert result.status_code == 200
    assert '"content": "Gambar"' in result.text

def test_invalid_image_message():
    for image_url in ['data:image/svg+xml;base64,aGk=', 'data:image/png;base64,not-base64']:
        content=[{'type':'image_url','image_url':{'url':image_url}}]
        assert client.post('/api/chat',json={**PAYLOAD,'messages':[{'role':'user','content':content}]}).status_code == 422
    too_many_images=[{'type':'image_url','image_url':{'url':'data:image/png;base64,iVBORw0KGgo='}} for _ in range(5)]
    assert client.post('/api/chat',json={**PAYLOAD,'messages':[{'role':'user','content':too_many_images}]}).status_code == 422

def test_connection_failure(monkeypatch):
    def handler(request):
        raise httpx.ConnectError('offline',request=request)
    mock_lm(monkeypatch,handler)
    assert client.get('/api/health').json()['lm_studio'] is False
    assert lmstudio.UNAVAILABLE in client.post('/api/chat',json=PAYLOAD).text

def test_health_exact_model(monkeypatch):
    mock_lm(monkeypatch,lambda request: httpx.Response(200,json={'data':[{'id':lmstudio.settings.lm_studio_model}]}))
    assert client.get('/api/health').json()['lm_studio'] is True

def test_truncated_stream(monkeypatch):
    mock_lm(monkeypatch,lambda request: httpx.Response(200,text='data: {"choices":[{"delta":{"content":"Sebagian"}}]}\n\n'))
    result=client.post('/api/chat',json=PAYLOAD)
    assert '"type": "error"' in result.text
    assert '"type": "done"' not in result.text

def test_cors():
    response=client.options('/api/chat',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in response.headers
