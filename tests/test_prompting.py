from app.prompting import generate_structured_metadata


def test_generate_structured_metadata_basic():
    info = {"width": 640, "height": 480, "format": "JPEG", "mode": "RGB"}
    meta = generate_structured_metadata(info, category="Ceramic Mug", platform="etsy", style="handmade")
    assert isinstance(meta, dict)
    assert "title" in meta and isinstance(meta["title"], str)
    assert "bullets" in meta and isinstance(meta["bullets"], list) and len(meta["bullets"]) == 3
    assert "description" in meta and isinstance(meta["description"], str)
    assert "tags" in meta and isinstance(meta["tags"], list)
    assert "attributes" in meta and isinstance(meta["attributes"], dict)
    assert meta["attributes"]["width"] == 640
    assert "handmade" in meta["tags"]
