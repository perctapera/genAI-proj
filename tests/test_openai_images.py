import os
import pytest
from app.openai_utils import generate_images


def _has_valid_openai_key():
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return False
    # common placeholders/masked keys contain '*' or words like 'placeholder' or 'your'
    if '*' in key:
        return False
    lk = key.lower()
    if 'placeholder' in lk or 'your' in lk or 'replace' in lk:
        return False
    return True


@pytest.mark.skipif(not _has_valid_openai_key(), reason='OPENAI_API_KEY not set or appears to be a masked placeholder')
def test_generate_images_ok():
    try:
        out = generate_images('A minimal white ceramic mug on a wooden table', n=1, outdir='outputs/test_images')
    except RuntimeError as e:
        msg = str(e).lower()
        # If OpenAI returns a server-side error (transient), skip rather than fail the test
        if 'server_error' in msg or '500' in msg or 'server had an error' in msg:
            pytest.skip('OpenAI server-side error (transient); skipping test')
        raise

    assert isinstance(out, list) and len(out) == 1
    assert os.path.exists(out[0])
