import io
import json
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("PIL")
from fastapi.testclient import TestClient
from app.main import app
from PIL import Image

client = TestClient(app)


def create_sample_image_file():
    img = Image.new("RGB", (200, 120), color=(123, 111, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return ("edited.jpg", buf, "image/jpeg")


def test_ingest_creates_listing_and_listings_endpoint():
    img = create_sample_image_file()
    data = {"description": "A great listing from n8n", "metadata": json.dumps({"title": "From n8n", "tags": ["n8n", "import"]})}
    files = {"files": img}
    res = client.post("/api/ingest-edits", data=data, files=files)
    assert res.status_code == 200
    payload = res.json()
    assert payload["description"] == data["description"]
    assert "listing" in payload

    # Fetch via the listings endpoint
    list_res = client.get("/api/listings")
    assert list_res.status_code == 200
    listings = list_res.json().get("listings", [])
    assert any(l.get("path") == payload["listing"] for l in listings)

    # Validate the stored listing data
    listing_entries = [l for l in listings if l.get("path") == payload["listing"]]
    assert len(listing_entries) == 1
    data_obj = listing_entries[0]["data"]
    assert data_obj["description"] == data["description"]
    assert "metadata" in data_obj and data_obj["metadata"]["title"] == "From n8n"
