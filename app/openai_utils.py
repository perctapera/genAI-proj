import os
import base64
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

OPENAI_IMAGES_ENDPOINT = "https://api.openai.com/v1/images/generations"
OPENAI_IMAGES_EDITS_ENDPOINT = "https://api.openai.com/v1/images/edits"


def _get_api_key():
    return os.getenv("OPENAI_API_KEY")


def generate_images(prompt: str, n: int = 3, size: str = "1024x1024", outdir: str | Path | None = None) -> list:
    """Generate `n` images from prompt using OpenAI Images API (direct HTTP call).

    Returns a list of saved file paths.
    """
    key = _get_api_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "n": n, "size": size}
    resp = requests.post(OPENAI_IMAGES_ENDPOINT, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        logger.error("OpenAI images API error: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"OpenAI images API error: {resp.status_code} {resp.text}")

    j = resp.json()
    data = j.get("data") or []
    outdir = Path(outdir or Path.cwd() / "outputs" / "images")
    outdir.mkdir(parents=True, exist_ok=True)
    out_paths = []
    for i, item in enumerate(data):
        b64 = item.get("b64_json") or item.get("b64") or item.get("b64_png")
        if not b64:
            # Some responses may include a url instead
            url = item.get("url")
            if url:
                # Download it
                r2 = requests.get(url, timeout=60)
                p = outdir / f"image_{i:03d}.jpg"
                with open(p, "wb") as f:
                    f.write(r2.content)
                out_paths.append(str(p))
                continue
            else:
                continue
        img_bytes = base64.b64decode(b64)
        p = outdir / f"image_{i:03d}.jpg"
        with open(p, "wb") as f:
            f.write(img_bytes)
        out_paths.append(str(p))
    return out_paths


def generate_variations_from_image(image_path: str, prompt: str | None = None, n: int = 3, size: str = "1024x1024", outdir: str | Path | None = None) -> list:
    """Generate variations based on an input image via OpenAI Images Edits endpoint.

    Returns a list of saved file paths, or an empty list on failure.
    """
    key = _get_api_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")

    headers = {"Authorization": f"Bearer {key}"}
    outdir = Path(outdir or Path.cwd() / "outputs" / "images")
    outdir.mkdir(parents=True, exist_ok=True)
    files = []
    try:
        # OpenAI edits endpoint prefers PNG inputs; convert to PNG in-memory to ensure compatibility
        from PIL import Image
        from io import BytesIO
        with Image.open(image_path) as im:
            buf = BytesIO()
            im.convert("RGBA").save(buf, format="PNG")
            buf.seek(0)
            files = [("image", ("image.png", buf, "image/png"))]
            data = {}
            if prompt:
                data["prompt"] = prompt
            data["n"] = n
            data["size"] = size
            # multipart upload: files + fields
            resp = requests.post(OPENAI_IMAGES_EDITS_ENDPOINT, headers=headers, files=files, data=data, timeout=120)
            if resp.status_code != 200:
                logger.error("OpenAI images edit API error: %s %s", resp.status_code, resp.text)
                raise RuntimeError(f"OpenAI images edit API error: {resp.status_code} {resp.text}")
            j = resp.json()
            data_items = j.get("data") or []
            out_paths = []
            for i, item in enumerate(data_items):
                b64 = item.get("b64_json") or item.get("b64") or item.get("b64_png")
                if not b64:
                    url = item.get("url")
                    if url:
                        r2 = requests.get(url, timeout=60)
                        p = outdir / f"edit_{i:03d}.jpg"
                        with open(p, "wb") as f2:
                            f2.write(r2.content)
                        out_paths.append(str(p))
                        continue
                    else:
                        continue
                img_bytes = base64.b64decode(b64)
                p = outdir / f"edit_{i:03d}.jpg"
                with open(p, "wb") as f2:
                    f2.write(img_bytes)
                out_paths.append(str(p))
            return out_paths
    except Exception as e:
        logger.exception("generate_variations_from_image failed: %s", e)
        return []
