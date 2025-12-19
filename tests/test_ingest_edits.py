import io
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("PIL")
from fastapi.testclient import TestClient
from app.main import app
from PIL import Image

client = TestClient(app)


def create_sample_image_bytes():
    img = Image.new("RGB", (200, 150), color=(200, 100, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_ingest_edits_single_file():
    img = create_sample_image_bytes()
    files = {"files": ("edited.jpg", img, "image/jpeg")}
    data = {"description": "Edited with OpenAI: brighter colors"}
    res = client.post("/api/ingest-edits", files=files, data=data)
    assert res.status_code == 200
    payload = res.json()
    assert payload["description"] == data["description"]
    assert isinstance(payload["images"], list)
    assert len(payload["images"]) == 1
    assert payload["images"][0].startswith("/outputs/supplementary/")
