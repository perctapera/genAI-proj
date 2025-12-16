import pytest
pytest.importorskip('fastapi')
import os
from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path

client = TestClient(app)


def test_generate_visuals_endpoint(tmp_path, monkeypatch):
    # create a sample image in uploads
    uploads = Path(os.path.dirname(os.path.dirname(__file__))) / 'data' / 'uploads'
    uploads.mkdir(parents=True, exist_ok=True)
    sample = tmp_path / 'sample.jpg'
    from PIL import Image
    im = Image.new('RGB', (320, 240), color=(120, 100, 80))
    im.save(sample)
    dest = uploads / 'sample_for_api.jpg'
    dest.write_bytes(sample.read_bytes())

    res = client.post('/api/generate-visuals', json={'image_path': str(dest), 'title':'API Test'})
    assert res.status_code == 200
    j = res.json()
    assert 'generated' in j and isinstance(j['generated'], list)
    assert len(j['generated']) > 0
    # ensure outputs exist on disk
    for p in j['generated']:
        path = Path(os.path.dirname(os.path.dirname(__file__))) / p
        assert path.exists()
