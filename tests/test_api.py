import io
import os
from importlib import reload

from fastapi.testclient import TestClient

import app.utils.auth as auth_module
import app.main as main_module


def build_client(api_key: str | None = None):
    if api_key is None:
        os.environ.pop('API_KEY', None)
    else:
        os.environ['API_KEY'] = api_key
    reload(auth_module)
    reload(main_module)
    return TestClient(main_module.app)


def test_healthz():
    client = build_client()
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_desensitize_text_file_success():
    client = build_client()
    data = '张三 13812345678 test@example.com'.encode('utf-8')
    response = client.post('/api/v1/desensitize', files={'file': ('sample.txt', io.BytesIO(data), 'text/plain')})
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'success'
    assert 'bundle_file' in payload


def test_desensitize_requires_api_key_when_enabled():
    client = build_client('secret-key')
    data = '张三 13812345678'.encode('utf-8')
    response = client.post('/api/v1/desensitize', files={'file': ('sample.txt', io.BytesIO(data), 'text/plain')})
    assert response.status_code == 401


def test_desensitize_accepts_api_key_when_enabled():
    client = build_client('secret-key')
    data = '张三 13812345678'.encode('utf-8')
    response = client.post(
        '/api/v1/desensitize',
        files={'file': ('sample.txt', io.BytesIO(data), 'text/plain')},
        headers={'x-api-key': 'secret-key'}
    )
    assert response.status_code == 200
