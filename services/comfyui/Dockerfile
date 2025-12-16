FROM python:3.11-slim
WORKDIR /comfyui
# Lightweight server to expose node_graphs and docs for demos in lieu of a full ComfyUI install
COPY ./app ./app
RUN pip install --no-cache-dir flask
EXPOSE 8188
CMD ["python", "-u", "app/server.py"]
