from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import os
import uuid
import shutil
from PIL import Image
import json
import random
import logging
from .prompting import generate_structured_metadata
from pathlib import Path

try:
    import openai
except Exception:
    openai = None

app = FastAPI(title="AI Product Listing Generator - Microservice")

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploads")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Mount static and upload folders
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

logger = logging.getLogger("uvicorn")


def save_upload_file(upload_file: UploadFile) -> str:
    filename = f"{uuid.uuid4().hex}_{upload_file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return path


def analyze_image(path: str) -> dict:
    with Image.open(path) as img:
        return {"width": img.width, "height": img.height, "mode": img.mode, "format": getattr(img, "format", "unknown")}


from .validation import is_valid_metadata, repair_with_openai, METADATA_SCHEMA


def fallback_generate_metadata(info: dict, category: str | None = None, platform: str = "generic") -> dict:
    """Wrapper that defers to the template-driven generator in `app.prompting`.

    Keeps behavior CPU-friendly and deterministic for the demo.
    """
    meta = generate_structured_metadata(info, category=category, platform=platform)
    meta["ai_used"] = False
    return meta


async def try_ai_generate(prompt: str) -> dict | None:
    """Attempt to generate JSON via OpenAI and validate/repair it to match METADATA_SCHEMA.

    Returns the parsed JSON dict if successful, otherwise None.
    """
    ai_text = await openai_generate(prompt)
    if not ai_text:
        return None
    try:
        parsed = json.loads(ai_text)
    except Exception:
        # try to repair using OpenAI ChatCompletion
        repaired = await repair_with_openai(openai, ai_text)
        if not repaired:
            return None
        try:
            parsed = json.loads(repaired)
        except Exception:
            return None
    valid, err = is_valid_metadata(parsed)
    if valid:
        parsed["ai_used"] = True
        return parsed
    # attempt to repair using openai
    repaired = await repair_with_openai(openai, ai_text)
    if not repaired:
        return None
    try:
        parsed = json.loads(repaired)
        valid, err = is_valid_metadata(parsed)
        if valid:
            parsed["ai_used"] = True
            return parsed
    except Exception:
        return None
    return None


async def openai_generate(prompt: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key or openai is None:
        return None
    openai.api_key = key
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an assistant that returns a single valid JSON object given the user's request."}, {"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=400,
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.error("OpenAI call failed: %s", e)
        return None


@app.get("/health")
def health():
    return {"status": "ok"}


from fastapi.responses import HTMLResponse
from fastapi import Request
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    tpl = jinja_env.get_template("index.html")
    return tpl.render()


@app.post("/api/generate-visuals")
async def api_generate_visuals(payload: dict):
    """Accepts JSON: {"image_path": "<path>", "title": "..."} Returns JSON with generated file URLs (served under /outputs).
    """
    from scripts.generate_supplementary_visuals import generate_variants
    image_path = payload.get("image_path")
    title = payload.get("title", "Product")
    if not image_path:
        return {"error": "image_path is required"}, 400
    # If the image path is from a local absolute or relative path, normalize; if it points to uploads, resolve
    if image_path.startswith("/") or image_path.startswith("\\") or os.path.isabs(image_path):
        abs_path = image_path
        if image_path.startswith("/uploads/"):
            abs_path = os.path.join(PROJECT_ROOT, image_path.lstrip("/"))
    else:
        # Assume it's a path to a file saved in uploads (e.g., c:\... or data/uploads/...)
        abs_path = image_path
    # Allow passing either the stored path or just filename
    attempted = []
    if not os.path.exists(abs_path):
        # try with uploads dir
        try_path = os.path.join(UPLOAD_DIR, os.path.basename(image_path))
        attempted.append(try_path)
        if os.path.exists(try_path):
            abs_path = try_path
        else:
            # also try common Docker-mounted path (/data/uploads)
            docker_path = os.path.join('/data/uploads', os.path.basename(image_path))
            attempted.append(docker_path)
            if os.path.exists(docker_path):
                abs_path = docker_path
            else:
                logger.error("generate-visuals: image not found. attempted: %s", attempted)
                return {"error": f"image not found: {image_path}", "attempted": attempted}, 404
    outdir = os.path.join(OUTPUTS_DIR, "supplementary")
    os.makedirs(outdir, exist_ok=True)
    # If an OpenAI API key is present, attempt to generate variations using the image edit endpoint
    from app.openai_utils import generate_variations_from_image
    generated = []
    if os.getenv('OPENAI_API_KEY'):
        try:
            prompt_hint = f"Create {5} product-focused variations of the provided image, keep the main subject consistent and present the item on a clean background. Title: {title}"
            generated = generate_variations_from_image(abs_path, prompt=prompt_hint, n=5, size="1024x1024", outdir=outdir)
        except Exception:
            logger.exception("openai variations failed; falling back to local PIL variants")
            generated = []

    if not generated:
        try:
            generated = generate_variants(Path(abs_path), Path(outdir), title=title, frames=5)
        except Exception as e:
            logger.exception("visual generation failed for %s", abs_path)
            return {"error": "visual generation failed", "details": str(e)}, 500

    # return web-accessible URLs (relative to server root)
    web_paths = [os.path.relpath(p, PROJECT_ROOT).replace('\\', '/') for p in generated]
    return {"generated": web_paths}


@app.post("/api/generate-video")
async def api_generate_video(payload: dict):
    """Create a slideshow video. Can accept either `frames` (list of frame paths), or a `prompt` to generate images via OpenAI.

    Optional keys:
      - frames: list of image paths
      - prompt: text prompt to generate images (requires OPENAI_API_KEY)
      - tts: text to synthesize narration (optional)
      - fps: frames per second (default 2)
    """
    from app.openai_utils import generate_images
    from app.video_utils import create_tts_audio, create_silent_audio, make_video_from_frames

    frames = payload.get("frames") or []
    prompt = payload.get("prompt")
    tts = payload.get("tts")
    fps = int(payload.get("fps", 2))

    # If prompt provided and no frames, generate images
    if not frames and prompt:
        try:
            img_outdir = os.path.join(OUTPUTS_DIR, "images")
            generated_imgs = generate_images(prompt, n=5, outdir=img_outdir)
            frames = generated_imgs
        except Exception as e:
            logger.exception("openai image generation failed")
            return {"error": "openai image generation failed", "details": str(e)}, 500

    if not frames:
        return {"error": "frames or prompt required"}, 400

    # Resolve frame absolute paths
    abs_frames = []
    for f in frames:
        p = f
        if p.startswith("/outputs/"):
            p = os.path.join(PROJECT_ROOT, p.lstrip("/"))
        if not os.path.exists(p):
            p = os.path.join(OUTPUTS_DIR, os.path.basename(p))
        if not os.path.exists(p):
            return {"error": f"frame not found: {f}"}, 404
        abs_frames.append(p)

    # Prepare audio: attempt TTS, else generate silent audio of appropriate duration
    audio_path = None
    if tts:
        try:
            audio_out = os.path.join(OUTPUTS_DIR, "audio")
            os.makedirs(audio_out, exist_ok=True)
            audio_path = os.path.join(audio_out, f"tts_{uuid.uuid4().hex[:8]}.mp3")
            create_tts_audio(tts, audio_path)
        except Exception as e:
            logger.warning("TTS failed: %s; falling back to silent audio", e)
            try:
                audio_path = os.path.join(OUTPUTS_DIR, "audio", f"silent_{uuid.uuid4().hex[:8]}.mp3")
                # estimate duration roughly by frames/fps
                duration = max(1, int(len(abs_frames) / max(1, fps)))
                create_silent_audio(audio_path, duration=duration)
            except Exception as e2:
                logger.warning("Silent audio generation failed: %s; proceeding without audio", e2)
                audio_path = None
    else:
        # no TTS, but create short silent audio so videos have an audio track (optional)
        try:
            audio_path = os.path.join(OUTPUTS_DIR, "audio", f"silent_{uuid.uuid4().hex[:8]}.mp3")
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            duration = max(1, int(len(abs_frames) / max(1, fps)))
            create_silent_audio(audio_path, duration=duration)
        except Exception:
            audio_path = None

    # Build video
    try:
        out_videos = os.path.join(OUTPUTS_DIR, "videos")
        os.makedirs(out_videos, exist_ok=True)
        out_path = os.path.join(out_videos, f"slideshow_{uuid.uuid4().hex[:8]}.mp4")
        final = make_video_from_frames(abs_frames, out_path, fps=fps, audio_path=audio_path)
    except Exception as e:
        logger.exception("video generation failed")
        return {"error": "video generation failed", "details": str(e)}, 500

    web_path = os.path.relpath(final, PROJECT_ROOT).replace('\\', '/')
    return {"video_url": '/' + web_path}

@app.post("/generate-metadata")
async def generate_metadata(file: UploadFile = File(...), category: str | None = Form(None), platform: str = Form("generic")):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    path = save_upload_file(file)
    info = analyze_image(path)

    prompt = (
        f"Produce a JSON object with keys: title (short string), bullets (array of 3 concise bullet points),"
        f" description (short marketing paragraph), tags (array), and attributes (object), based on the following image metadata:"
        f" width={info['width']}, height={info['height']}, format={info['format']}, mode={info['mode']}."
        f" Category: {category or 'N/A'}. Platform: {platform}."
        f" The JSON must conform to this schema: {json.dumps(METADATA_SCHEMA)}. Return only a single valid JSON object."
    )

    # Try AI-first generation + validation
    ai_result = await try_ai_generate(prompt)
    if ai_result:
        ai_result["image_path"] = path
        return ai_result

    # Fallback if AI unavailable or failed
    result = fallback_generate_metadata(info, category, platform)
    result["image_path"] = path
    return result
