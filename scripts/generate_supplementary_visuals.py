"""Generate CPU-friendly supplementary visuals (fallback for ComfyUI) using PIL.

Produces multiple stylized variants from an input image and saves frames for a short slideshow.
"""
import argparse
import json
import os
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont


def ensure_outdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def apply_sepia(im: Image.Image) -> Image.Image:
    gray = im.convert("L")
    sep = Image.new("RGB", im.size)
    pixels = sep.load()
    gpx = gray.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            v = gpx[x, y]
            r = int(v * 0.95)
            g = int(v * 0.85)
            b = int(v * 0.65)
            pixels[x, y] = (r, g, b)
    return sep


def add_vignette(im: Image.Image) -> Image.Image:
    width, height = im.size
    vign = Image.new("L", im.size, 0)
    draw = ImageDraw.Draw(vign)
    maxrad = min(width, height)
    for i in range(0, maxrad//2, 10):
        # avoid coordinates where y1 < y0 by bounding to min(width,height)
        draw.ellipse((i, i, width - i, height - i), fill=255 - int(255 * (i / (maxrad//2))))
    vign = vign.filter(ImageFilter.GaussianBlur(radius=max(1, width//30)))
    im_rgb = im.convert("RGB")
    im_rgb.putalpha(vign)
    bg = Image.new("RGB", im.size, (10, 10, 10))
    bg.paste(im_rgb, mask=im_rgb.split()[3])
    return bg


def overlay_text(im: Image.Image, text: str = "Sample Product", position: str = "bottom-right") -> Image.Image:
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", size=max(16, im.size[0] // 32))
    except Exception:
        font = ImageFont.load_default()
    # Compatible sizing across Pillow versions
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        try:
            w, h = font.getsize(text)
        except Exception:
            w, h = (len(text) * 6, 12)
    padding = 10
    x = im.size[0] - w - padding
    y = im.size[1] - h - padding
    draw.rectangle(((x - 6, y - 6), (x + w + 6, y + h + 6)), fill=(0, 0, 0, 120))
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    return im


def generate_variants(input_path: Path, outdir: Path, title: str = "Handmade Product", frames: int = 5) -> list:
    ensure_outdir(outdir)
    im = Image.open(input_path).convert("RGB")
    outputs = []

    # Variant 1: color boosted
    im1 = ImageEnhance.Color(im).enhance(1.4)
    im1 = ImageEnhance.Contrast(im1).enhance(1.1)
    im1 = overlay_text(im1.copy(), title)
    p1 = outdir / (input_path.stem + "_colorboost.jpg")
    im1.save(p1, quality=90)
    outputs.append(str(p1))

    # Variant 2: sepia + vignette
    im2 = apply_sepia(im)
    im2 = add_vignette(im2)
    p2 = outdir / (input_path.stem + "_sepia_vignette.jpg")
    im2.save(p2, quality=90)
    outputs.append(str(p2))

    # Variant 3: stylized blur + border
    im3 = im.filter(ImageFilter.GaussianBlur(radius=2))
    im3 = ImageEnhance.Color(im3).enhance(1.2)
    border = Image.new("RGB", (im3.size[0] + 20, im3.size[1] + 20), (240, 238, 235))
    border.paste(im3, (10, 10))
    p3 = outdir / (input_path.stem + "_styled_frame.jpg")
    border.save(p3, quality=90)
    outputs.append(str(p3))

    # Sequence frames for simple slideshow (scale + slight rotate)
    frame_paths = []
    for i in range(frames):
        f = im.copy()
        scale = 1 + i * 0.02
        new_size = (int(f.width * scale), int(f.height * scale))
        f = f.resize(new_size, Image.LANCZOS)
        f = f.rotate(i * 2, expand=True)
        # center crop back to original size
        left = (f.width - im.width) // 2
        top = (f.height - im.height) // 2
        f = f.crop((left, top, left + im.width, top + im.height))
        fn = outdir / f"{input_path.stem}_frame_{i:02d}.jpg"
        f.save(fn, quality=85)
        frame_paths.append(str(fn))
    outputs.extend(frame_paths)

    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=None, help="Input image path (defaults to sample created)")
    parser.add_argument("--outdir", type=str, default="outputs/supplementary", help="Output directory")
    parser.add_argument("--title", type=str, default="Handmade Product", help="Overlay title text")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    ensure_outdir(outdir)

    if args.input is None:
        # create a sample image
        tmp = outdir / "sample_input.jpg"
        im = Image.new("RGB", (800, 600), color=(200, 180, 160))
        draw = ImageDraw.Draw(im)
        draw.text((40, 40), "Sample Product", fill=(50, 30, 20))
        im.save(tmp, quality=90)
        input_path = tmp
    else:
        input_path = Path(args.input)

    paths = generate_variants(input_path, outdir, title=args.title)
    print(json.dumps({"generated": paths}, indent=2))


if __name__ == "__main__":
    main()
