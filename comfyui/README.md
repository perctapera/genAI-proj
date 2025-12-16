ComfyUI pipelines (CPU-friendly)

This folder contains:
- `node_graphs/supplementary_visuals.json` — an exported node layout example that demonstrates a lightweight node chain for generating supplementary images (image loader → color balance → resize → simple stylize → save) that can be imported into ComfyUI or used as documentation for designing similar graphs.

CPU-friendly guidance
- For demos without GPU, use small or CPU-compatible models, or run node graphs that operate on images without heavy diffusion (color operations, resize, filtering, overlays).
- If you want fully automated visual generation without GPU in this repo, use the provided PIL fallback script `scripts/generate_supplementary_visuals.py` which produces attractive variants and a short frame sequence for video.

Notes
- The `node_graphs` JSON is illustrative: if you use ComfyUI installed locally, adapt node IDs and model references for your environment.
- Export screenshots of your node graphs into `comfyui/screenshots/` and place final results in `outputs/supplementary/` for documentation.
