import pytest
pytest.importorskip('jsonschema')
from app.validation import is_valid_metadata, METADATA_SCHEMA


def test_valid_sample():
    sample = {
        "title": "Stylish Ceramic Mug",
        "bullets": ["Handmade", "Microwave safe", "12 oz capacity"],
        "description": "A beautiful ceramic mug perfect for coffee lovers.",
        "tags": ["ceramic", "mug", "kitchen"],
        "attributes": {"color": "white", "material": "ceramic"}
    }
    ok, err = is_valid_metadata(sample)
    assert ok


def test_missing_required():
    bad = {"title": "No bullets"}
    ok, err = is_valid_metadata(bad)
    assert not ok
    assert "bullets" in err or "is a required property" in err
