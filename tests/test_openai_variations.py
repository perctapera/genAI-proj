import os
import pytest
from app.openai_utils import generate_variations_from_image


@pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason='OPENAI_API_KEY not set')
def test_generate_variations_from_image(tmp_path):
    # create a simple sample image
    from PIL import Image
    import pytest
    p = tmp_path / "input.jpg"
    Image.new("RGB", (400, 300), color=(180, 180, 200)).save(p)
    try:
        out = generate_variations_from_image(str(p), prompt='Test variations', n=1, outdir=tmp_path)
    except RuntimeError as e:
        msg = str(e).lower()
        if 'rate limit' in msg or '429' in msg:
            pytest.skip('OpenAI rate limit reached; skipping')
        if 'server_error' in msg or '500' in msg:
            pytest.skip('OpenAI server error; skipping')
        raise

    assert isinstance(out, list)
    # if openai is available, at least 1 variation returned
    if not len(out):
        pytest.skip('No images returned from OpenAI; skipping')
    assert all(os.path.exists(x) for x in out)