import io
import pytest
pytest.importorskip("rembg")
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


def test_remove_background_returns_png_and_has_alpha():
    img_buf = create_sample_image_bytes()
    files = {"file": ("input.jpg", img_buf, "image/jpeg")}
    res = client.post("/api/remove-background", files=files)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/png")

    img = Image.open(io.BytesIO(res.content))
    # Should be RGBA (alpha channel present)
    assert img.mode == "RGBA"
    # Alpha channel should exist and have at least one non-opaque pixel (some transparency)
    alpha = img.getchannel("A")
    min_alpha, max_alpha = alpha.getextrema()
    assert min_alpha < 255
