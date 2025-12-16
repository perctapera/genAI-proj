import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from app.main import app
from PIL import Image
import io

client = TestClient(app)


def create_sample_image_bytes():
    img = Image.new("RGB", (400, 300), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_generate_metadata_basic():
    img_bytes = create_sample_image_bytes()
    files = {"file": ("sample.jpg", img_bytes, "image/jpeg")}
    data = {"category": "Handmade Mug", "platform": "etsy"}
    res = client.post("/generate-metadata", files=files, data=data)
    assert res.status_code == 200
    payload = res.json()
    assert "title" in payload
    assert "bullets" in payload and isinstance(payload["bullets"], list)
    assert "description" in payload
    assert "tags" in payload and isinstance(payload["tags"], list)
    assert "attributes" in payload and isinstance(payload["attributes"], dict)
    assert "image_path" in payload
