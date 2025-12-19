from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
import os
import uuid
import shutil
from PIL import Image
import json
import logging
from .prompting import generate_structured_metadata
from pathlib import Path

try:
    import openai
except Exception:
    openai = None

app = FastAPI(title="AI Product Listing Generator - Microservice")

# Use /data directory for persistent storage in Docker
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = "/data/uploads"
OUTPUTS_DIR = "/data/outputs"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "supplementary"), exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "audio"), exist_ok=True)

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and data directories
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

logger = logging.getLogger("uvicorn")


def save_upload_file(upload_file: UploadFile) -> str:
    filename = f"{uuid.uuid4().hex}_{upload_file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return filename  # Return just the filename, not full path


def analyze_image(filename: str) -> dict:
    full_path = os.path.join(UPLOAD_DIR, filename)
    with Image.open(full_path) as img:
        return {"width": img.width, "height": img.height, "mode": img.mode, "format": getattr(img, "format", "unknown")}


from .validation import is_valid_metadata, repair_with_openai, METADATA_SCHEMA


def fallback_generate_metadata(info: dict, category: str | None = None, platform: str = "generic") -> dict:
    """Wrapper that defers to the template-driven generator in `prompting`."""
    meta = generate_structured_metadata(info, category=category, platform=platform)
    meta["ai_used"] = False
    return meta


async def try_ai_generate(prompt: str) -> dict | None:
    """Attempt to generate JSON via OpenAI and validate/repair it to match METADATA_SCHEMA."""
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
    # Keep response minimal to match tests and healthcheck expectations
    return {"status": "ok"}


from fastapi.responses import HTMLResponse
from fastapi import Request
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@app.get("/")
def index(request: Request):
    """Serve the main UI from the templates directory.

    The previous implementation tried to open "index.html" from the CWD,
    which fails in Docker where the working directory is /app. Use the
    configured Jinja2 loader rooted at app/templates instead.
    """
    template = jinja_env.get_template("index.html")
    return HTMLResponse(content=template.render())


@app.post("/api/generate-visuals")
async def api_generate_visuals(payload: dict):
    """Generate supplementary visuals for a product image."""
    # Accept multiple input shapes for backwards/forwards compatibility
    image_filename = payload.get("image_filename")
    image_path = payload.get("image_path") or payload.get("image_url")
    title = payload.get("title", "Product")
    
    if not image_filename:
        if image_path:
            image_filename = os.path.basename(image_path)
        else:
            raise HTTPException(status_code=400, detail="image_filename or image_path is required")
    
    image_path = os.path.join(UPLOAD_DIR, image_filename)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {image_filename}")
    
    outdir = os.path.join(OUTPUTS_DIR, "supplementary")
    os.makedirs(outdir, exist_ok=True)
    
    generated = []
    
    # Try OpenAI variations if API key is available
    if os.getenv('OPENAI_API_KEY'):
        try:
            from .openai_utils import generate_variations_from_image
            prompt_hint = f"Create product-focused variations of the provided image, keep the main subject consistent and present the item on a clean background. Title: {title}"
            generated = generate_variations_from_image(image_path, prompt=prompt_hint, n=5, size="1024x1024", outdir=outdir)
        except Exception as e:
            logger.exception("OpenAI variations failed: %s", e)
            generated = []
    
    # Fallback to local PIL variants
    if not generated:
        try:
            # Simple image manipulation as fallback
            from PIL import Image, ImageEnhance, ImageFilter
            import random
            
            img = Image.open(image_path)
            
            # Create variations
            for i in range(5):
                variant = img.copy()
                
                # Apply random transformations
                # Random crop
                width, height = variant.size
                left = random.randint(0, width // 4)
                top = random.randint(0, height // 4)
                right = width - random.randint(0, width // 4)
                bottom = height - random.randint(0, height // 4)
                variant = variant.crop((left, top, right, bottom))
                
                # Resize back to original
                variant = variant.resize((width, height), Image.Resampling.LANCZOS)
                
                # Random color adjustments
                if random.random() > 0.5:
                    enhancer = ImageEnhance.Brightness(variant)
                    variant = enhancer.enhance(random.uniform(0.8, 1.2))
                
                if random.random() > 0.5:
                    enhancer = ImageEnhance.Contrast(variant)
                    variant = enhancer.enhance(random.uniform(0.8, 1.2))
                
                if random.random() > 0.5:
                    enhancer = ImageEnhance.Color(variant)
                    variant = enhancer.enhance(random.uniform(0.8, 1.2))
                
                # Add background if transparent
                if variant.mode in ('RGBA', 'LA') or (variant.mode == 'P' and 'transparency' in variant.info):
                    background = Image.new('RGB', variant.size, (255, 255, 255))
                    if variant.mode == 'RGBA':
                        background.paste(variant, mask=variant.split()[3])
                    else:
                        background.paste(variant)
                    variant = background
                
                # Save the variant
                output_path = os.path.join(outdir, f"variant_{uuid.uuid4().hex[:8]}_{i}.jpg")
                variant.save(output_path, "JPEG", quality=85)
                generated.append(output_path)
                
        except Exception as e:
            logger.exception("Local visual generation failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Visual generation failed: {str(e)}")
    
    # Optionally remove backgrounds from generated images
    remove_bg = payload.get("remove_background", True)
    if remove_bg:
        try:
            from .image_utils import remove_background_bytes

            processed = []
            for p in generated:
                try:
                    with open(p, "rb") as fh:
                        data = fh.read()
                    out_bytes = remove_background_bytes(data)
                    # Save as PNG to preserve alpha channel
                    base = os.path.splitext(os.path.basename(p))[0]
                    png_name = f"{base}.png"
                    out_path = os.path.join(outdir, png_name)
                    with open(out_path, "wb") as fh:
                        fh.write(out_bytes)
                    processed.append(out_path)
                except Exception as e:
                    logger.exception("Background removal failed for %s: %s", p, e)
                    # Fall back to original
                    processed.append(p)
            generated = processed
        except ImportError:
            logger.info("rembg is not installed; skipping background removal")

    # Return web-accessible URLs
    web_paths = []
    for p in generated:
        # Get filename only for web path
        filename = os.path.basename(p)
        web_paths.append(f"/outputs/supplementary/{filename}")

    return {"success": True, "generated": web_paths}


@app.post("/api/generate-video")
async def api_generate_video(payload: dict):
    """Create a slideshow video from images."""
    # Accept both 'frames' and 'image_urls'
    image_urls = payload.get("frames") or payload.get("image_urls") or []
    title = payload.get("title", "Product Video")
    
    if not image_urls:
        raise HTTPException(status_code=400, detail="image_urls is required")
    
    # For Docker, we need to handle both local paths and URLs
    frame_paths = []
    
    for i, url in enumerate(image_urls):
        if url.startswith('/outputs/') or url.startswith('/uploads/'):
            # Local file in Docker volume
            local_path = f"/data{url}"  # Convert web path to Docker path
            if os.path.exists(local_path):
                frame_paths.append(local_path)
            else:
                logger.warning(f"File not found: {local_path}")
        else:
            # Handle data URLs or external URLs
            try:
                import requests
                import tempfile
                
                if url.startswith('data:'):
                    # Handle data URL
                    import base64
                    header, encoded = url.split(',', 1)
                    data = base64.b64decode(encoded)
                    
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                        f.write(data)
                        frame_paths.append(f.name)
                else:
                    # Handle HTTP URL
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                        f.write(response.content)
                        frame_paths.append(f.name)
            except Exception as e:
                logger.error(f"Failed to process image {url}: {e}")
    
    if not frame_paths:
        raise HTTPException(status_code=400, detail="No valid images to create video")
    
    # Create video
    try:
        from .video_utils import make_video_from_frames
        
        out_videos = os.path.join(OUTPUTS_DIR, "videos")
        os.makedirs(out_videos, exist_ok=True)
        out_path = os.path.join(out_videos, f"video_{uuid.uuid4().hex[:8]}.mp4")
        
        # Create video with frames
        final_path = make_video_from_frames(frame_paths, out_path, fps=2, audio_path=None)
        
        # Clean up temp files
        for path in frame_paths:
            if path.startswith('/tmp/'):
                try:
                    os.unlink(path)
                except:
                    pass
        
        # Return web-accessible URL
        filename = os.path.basename(final_path)
        web_url = f"/outputs/videos/{filename}"
        
        return {"success": True, "video_url": web_url}
        
    except Exception as e:
        logger.exception("Video generation failed: %s", e)
        # Clean up temp files on error
        for path in frame_paths:
            if path.startswith('/tmp/'):
                try:
                    os.unlink(path)
                except:
                    pass
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


# Primary endpoint used by the frontend
@app.post("/generate-metadata")
async def api_generate_metadata(
    file: UploadFile = File(...),
    category: str = Form(None),
    platform: str = Form("generic"),
    tone: str = Form("professional")
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    filename = save_upload_file(file)
    info = analyze_image(filename)

    # Generate metadata using OpenAI or fallback
    prompt = (
        f"Produce a JSON object with keys: title (short string), bullets (array of 3 concise bullet points),"
        f" description (short marketing paragraph), tags (array), and attributes (object), based on the following image metadata:"
        f" width={info['width']}, height={info['height']}, format={info['format']}, mode={info['mode']}."
        f" Category: {category or 'N/A'}. Platform: {platform}. Tone: {tone}."
        f" The JSON must conform to this schema: {json.dumps(METADATA_SCHEMA)}. Return only a single valid JSON object."
    )

    # Try AI-first generation + validation
    ai_result = await try_ai_generate(prompt)
    if ai_result:
        result = ai_result
    else:
        # Fallback if AI unavailable or failed
        result = fallback_generate_metadata(info, category, platform)
    
    # Add additional information
    result["image_filename"] = filename
    # Include fields used by both UI and tests
    result["image_url"] = f"/uploads/{filename}"
    result["image_path"] = f"/uploads/{filename}"
    result["category"] = category or "Generic Product"
    result["platform"] = platform
    result["tone"] = tone
    
    return result


# Ingest edited images and a description from an external workflow (e.g., n8n)
@app.post("/api/ingest-edits")
async def api_ingest_edits(
    description: str = Form(...),
    files: list[UploadFile] = File(None),
    metadata: str = Form(None),
):
    """Accept a description and one or more edited images (multipart/form-data).

    Saves images under `/data/outputs/supplementary`. If `metadata` (JSON string)
    is provided, a listing JSON is created and saved next to the images. The
    response includes the web-accessible paths and `listing` path when created.
    """
    outdir = os.path.join(OUTPUTS_DIR, "supplementary")
    os.makedirs(outdir, exist_ok=True)

    saved = []
    if files:
        # FastAPI provides a single UploadFile when single file is sent, or list when multiple
        if isinstance(files, UploadFile):
            files = [files]
        for f in files:
            safe_name = os.path.basename(f.filename)
            filename = f"edited_{uuid.uuid4().hex[:8]}_{safe_name}"
            dest = os.path.join(outdir, filename)
            with open(dest, "wb") as fh:
                shutil.copyfileobj(f.file, fh)
            saved.append(f"/outputs/supplementary/{filename}")

    listing_path = None
    if metadata:
        try:
            meta_obj = json.loads(metadata)
        except Exception:
            meta_obj = {"raw": metadata}

        # Combine description and provided metadata
        listing = {
            "description": description,
            "images": saved,
            "metadata": meta_obj,
        }

        listing_filename = f"listing_{uuid.uuid4().hex[:8]}.json"
        listing_dest = os.path.join(outdir, listing_filename)
        with open(listing_dest, "w", encoding="utf-8") as fh:
            json.dump(listing, fh, ensure_ascii=False, indent=2)

        listing_path = f"/outputs/supplementary/{listing_filename}"

    resp = {"description": description, "images": saved}
    if listing_path:
        resp["listing"] = listing_path

    return resp


@app.get("/api/listings")
async def api_listings():
    """Return all saved listings (JSON files) from the supplementary outputs folder."""
    outdir = os.path.join(OUTPUTS_DIR, "supplementary")
    listings = []
    if os.path.exists(outdir):
        for name in sorted(os.listdir(outdir)):
            if name.startswith("listing_") and name.endswith(".json"):
                path = os.path.join(outdir, name)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    listings.append({"path": f"/outputs/supplementary/{name}", "data": data})
                except Exception:
                    logger.exception("Failed to read listing %s", path)
    return {"listings": listings}


@app.post("/api/remove-background")
async def api_remove_background(file: UploadFile = File(...)):
    """Remove image background and return a PNG with transparency (alpha channel).

    If `rembg` is not installed, returns 501 with a helpful message.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    data = await file.read()

    try:
        from .image_utils import remove_background_bytes
    except ImportError:
        raise HTTPException(status_code=501, detail="Background removal not available: 'rembg' is not installed")

    try:
        out_bytes = remove_background_bytes(data)
    except Exception as e:
        logger.exception("Background removal failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Background removal failed: {e}")

    import io
    from fastapi.responses import StreamingResponse

    return StreamingResponse(io.BytesIO(out_bytes), media_type="image/png")


# Backwards-compatible alias (older clients may call the /api path)
@app.post("/api/generate-metadata")
async def api_generate_metadata_alias(
    file: UploadFile = File(...),
    category: str = Form(None),
    platform: str = Form("generic"),
    tone: str = Form("professional")
):
    return await api_generate_metadata(file=file, category=category, platform=platform, tone=tone)