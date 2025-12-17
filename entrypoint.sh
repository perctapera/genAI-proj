#!/bin/sh
set -e

# Ensure expected data directories exist and are writable
mkdir -p /data/uploads /data/outputs /data/outputs/videos /data/outputs/images /data/outputs/supplementary /data/outputs/audio

# If possible, make the app user own the data dir so writes succeed when volumes are mounted
chown -R appuser:appuser /data || true

# Exec the requested command as appuser (drop privileges)
if command -v su >/dev/null 2>&1; then
  exec su -s /bin/sh -c "$*" appuser
else
  # Fallback: run command directly (may run as root)
  exec "$@"
fi
