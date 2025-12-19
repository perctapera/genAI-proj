#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image and run the unit tests in the host environment
python -m pip install --upgrade pip
pip install -r requirements.txt
# Install dev/test requirements if provided (contains fastapi, pillow, etc.)
if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi
pytest -q

docker build . -t genai-proj-app:local-ci

echo "Local CI steps completed"