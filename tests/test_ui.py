import pytest
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_index_returns_html():
    res = client.get('/')
    assert res.status_code == 200
    assert 'AI Product Listing Generator' in res.text


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json() == {'status': 'ok'}
