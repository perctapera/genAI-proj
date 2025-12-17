FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal, no recommended packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    libgl1-mesa-dev \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories (used by both app AND optional docker mounts)
RUN mkdir -p /data/uploads /data/outputs /data/outputs/videos /data/outputs/images /data/outputs/supplementary /data/outputs/audio

# Create a non-root user and ensure ownership
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /data

# Copy and install entrypoint so we can fix ownership of mounted dirs at runtime
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

# Health check: use curl (installed above) and rely on exit code
# Use exec form for maximum compatibility
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["sh", "-c", "curl -fsS http://localhost:8000/health || exit 1"]

# Use entrypoint script which will chown /data and then execute the CMD as appuser
ENTRYPOINT ["/entrypoint.sh"]

# Run the application (the entrypoint will drop privileges to appuser)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]