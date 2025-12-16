# AI Product Listing Generator

[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml)


A minimal, CPU-friendly scaffold for an autonomous agent that generates e-commerce product listing metadata from images.

Features
- FastAPI microservice: `/generate-metadata` (image upload → structured JSON metadata)
- Optional OpenAI integration for richer, model-generated metadata when `OPENAI_API_KEY` is set
- Fallback rule-based generator so the demo runs without any API keys or GPU
- `docker-compose.yml` includes `app` and an n8n service for orchestration
- Basic test that uploads a generated sample image and validates JSON output

Quick Start (local, no Docker)
1. python -m venv .venv
2. pip install -r requirements.txt
3. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
4. POST an image to `http://localhost:8000/generate-metadata` with multipart `file` and optional form fields `category` and `platform`.

Docker (recommended for demo)
1. Copy `.env.example` to `.env` and add any keys (optional)
2. docker-compose up --build
3. n8n UI will be available at `http://localhost:5678` (see `n8n/workflow.json` for an example webhook)

Optional ComfyUI service
- To include the optional ComfyUI placeholder server (CPU-friendly), run: `docker compose --profile comfyui up --build`.
- The placeholder server is a lightweight Flask app that serves node graphs and screenshots (see `services/comfyui/`). For production or GPU-powered visual model runs, replace this service with a full ComfyUI container or custom Dockerfile supporting GPUs.
- When active, the placeholder is available at `http://localhost:8188/` and can be used to view node graphs and documentation.

n8n local workflow (file-storage example) ✅

- The included `n8n/workflow.json` implements a local-storage flow: **Webhook → Write Binary File → HTTP Request → Respond**.
  - The Webhook listens at `/webhook/generate-listing`.
  - **Important:** For Docker Compose users, ensure n8n writes to `/data/uploads/` (absolute path) and that `docker-compose.yml` mounts the host `./data/uploads` into the n8n container at `/data/uploads`.
  - Uploaded images are written to the shared `./data/uploads/` folder (local storage) using the **Write Binary File** node configured with `/data/uploads/{{$binary.data.fileName}}`.
  - The **HTTP Request** node then posts the saved binary to the microservice at `http://app:8000/generate-metadata` (works with Docker Compose network or if app is reachable locally).
  - The workflow responds to the original webhook caller with the JSON returned from the microservice.

Demo script
- Use `scripts/send_to_n8n.py` to POST a sample image to `http://localhost:5678/webhook/generate-listing` and print the microservice response.

Web UI
- Visit `http://localhost:8000/` to use the included web UI. Features:
  - Upload an image and generate metadata
  - Generate supplementary visuals (uses local PIL fallback)
  - Create a slideshow video (requires `ffmpeg` on PATH; the Docker image now installs `ffmpeg` during build)

Troubleshooting
- If `pip install -r requirements.txt` fails, ensure you're using a supported Python 3.9+ interpreter and a virtualenv:
  - python -m venv .venv
  - .\.venv\Scripts\activate    (Windows PowerShell: `.\.venv\Scripts\Activate.ps1`)
  - python -m pip install --upgrade pip setuptools wheel
  - pip install -r requirements.txt
- If `ffmpeg` is not found (video generation will fail), install it:
  - Windows: Use `choco install ffmpeg` (if using Chocolatey) or download a static build from https://ffmpeg.org and add it to PATH
  - macOS: `brew install ffmpeg`
  - Linux: use your package manager, e.g., `sudo apt install ffmpeg`
- If you see tests skipped due to missing dependencies, re-run `pip install -r requirements.txt` in your environment.

Notes

Notes
- The microservice contains a simple fallback generator that produces attractive, ready-to-use listing fields. When `OPENAI_API_KEY` is present, it will attempt to call the API to produce JSON; otherwise it uses the local generator.
- This scaffold is intentionally lightweight and CPU-friendly.

Next steps
- Add prompt templates and prompt orchestration layers
- Implement ComfyUI pipelines for supplementary images/videos (CPU-friendly guidance and a PIL fallback script are included)
- Add real tokens/keys handling and cloud storage (S3/GCS)


---

## Deployment & CI ✅

This repository includes a lightweight CI workflow that runs unit tests and performs a Docker build on push/PR to `main` (`.github/workflows/ci.yml`). To run locally:

- Run tests and build image:

```bash
./scripts/ci_build.sh
```

### Docker / Compose

1. Copy `.env.example` to `.env` and update any keys (optional):
   - `OPENAI_API_KEY` — if present and valid, OpenAI-dependent tests and E2E flows will run; masked or placeholder keys are ignored by tests.
2. Start the demo:

```bash
docker compose up --build
```

3. App UI: `http://localhost:8000/` — n8n UI: `http://localhost:5678/` (optional comfyui profile: `--profile comfyui`)

### Notes about OpenAI E2E tests

- Tests that call OpenAI are skipped when `OPENAI_API_KEY` is missing or appears to be a masked or placeholder value (e.g., contains `*` or words like `placeholder`). To run those tests in CI, add a repository secret `OPENAI_API_KEY`.

---

Enjoy! ✅