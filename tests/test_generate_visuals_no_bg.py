import io
import os
import pytest
pytest.importorskip("rembg")
pytest.importorskip("PIL")
from fastapi.testclient import TestClient
from app.main import app
from PIL import Image

client = TestClient(app)


def create_and_upload_image():
    img = Image.new("RGB", (300, 200), color=(150, 80, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    files = {"file": ("upload.jpg", buf, "image/jpeg")}
    # Use generate-metadata to store/upload an image and get filename
    res = client.post("/generate-metadata", files=files)
    assert res.status_code == 200
    payload = res.json()
    return payload["image_filename"]


def test_generate_visuals_removes_background():
    image_filename = create_and_upload_image()
    payload = {"image_filename": image_filename, "remove_background": True}
    res = client.post("/api/generate-visuals", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data.get("success") is True
    gen = data.get("generated")
    assert isinstance(gen, list) and len(gen) > 0

    # Fetch first generated image and assert it is PNG with RGBA and some transparent pixels
    first = gen[0]
    assert first.startswith("/outputs/supplementary/")

    r = client.get(first)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")

    img = Image.open(io.BytesIO(r.content))
    assert img.mode == "RGBA"
    alpha = img.getchannel("A")
    min_alpha, max_alpha = alpha.getextrema()
    assert min_alpha < 255
