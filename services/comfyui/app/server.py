from flask import Flask, send_from_directory, jsonify, render_template_string
import os
from pathlib import Path

app = Flask(__name__, static_folder=None)
BASE = Path('/comfyui')
NODE_DIR = BASE / 'node_graphs'
SCREEN_DIR = BASE / 'screenshots'

INDEX_HTML = """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>ComfyUI (Demo placeholder)</title></head>
  <body style="font-family:Arial,Helvetica,sans-serif;padding:24px;max-width:900px;">
    <h1>ComfyUI Demo Placeholder</h1>
    <p>This lightweight server hosts the example node graphs, screenshots, and notes shipped with the project. Replace this service with a real ComfyUI container for model-based generation (GPU recommended).</p>
    <h2>Available Node Graphs</h2>
    <ul>
    {% for f in files %}
      <li><a href="/node_graphs/{{ f }}">{{ f }}</a></li>
    {% endfor %}
    </ul>
    <h2>Screenshots (if present)</h2>
    <ul>
    {% for s in screens %}
      <li><a href="/screenshots/{{ s }}">{{ s }}</a></li>
    {% endfor %}
    </ul>
  </body>
</html>
"""


@app.route('/')
def index():
    files = []
    screens = []
    if NODE_DIR.exists():
        files = [p.name for p in NODE_DIR.glob('*.json')]
    if SCREEN_DIR.exists():
        screens = [p.name for p in SCREEN_DIR.glob('*')]
    return render_template_string(INDEX_HTML, files=files, screens=screens)


@app.route('/node_graphs/<path:name>')
def graphs(name):
    return send_from_directory(str(NODE_DIR), name)


@app.route('/screenshots/<path:name>')
def screens(name):
    return send_from_directory(str(SCREEN_DIR), name)


@app.route('/info')
def info():
    return jsonify({
        'service': 'ComfyUI demo placeholder',
        'note': 'Replace with a proper ComfyUI service for model-driven generation; this is CPU-friendly and lightweight.'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8188))
    app.run(host='0.0.0.0', port=port)
