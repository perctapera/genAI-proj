"""Image utility helpers (background removal, conversions)."""
from typing import Optional


def remove_background_bytes(data: bytes) -> bytes:
    """Remove background from image bytes using rembg.

    Returns PNG bytes with alpha channel.
    Raises ImportError if rembg is not installed.
    Raises Exception on processing errors.
    """
    try:
        from rembg import remove
    except Exception as e:
        raise ImportError("rembg is not installed") from e

    # rembg.remove accepts bytes and returns PNG bytes
    out = remove(data)
    return out
