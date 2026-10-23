import json
from pathlib import Path

WORKERS = json.loads((Path(__file__).resolve().parents[1] / 'shared/workers.json').read_text(encoding='utf-8'))
BY_ID = {worker['id']: worker for worker in WORKERS}
def public_workers():
    return [{k: v for k, v in worker.items() if k != 'system'} for worker in WORKERS]
