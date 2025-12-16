import json
from pathlib import Path
import tempfile
from scripts.generate_supplementary_visuals import generate_variants


def test_generate_variants_creates_files(tmp_path):
    # create a small sample image
    sample = tmp_path / "sample.jpg"
    from PIL import Image
    im = Image.new("RGB", (320, 240), color=(100, 120, 140))
    im.save(sample)

    outdir = tmp_path / "out"
    outdir.mkdir()
    paths = generate_variants(sample, outdir, title="Test Item", frames=3)
    assert len(paths) >= 3
    for p in paths:
        assert Path(p).exists()
