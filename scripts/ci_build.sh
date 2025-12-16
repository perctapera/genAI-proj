#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image and run the unit tests in the host environment
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q

docker build . -t genai-proj-app:local-ci

echo "Local CI steps completed"