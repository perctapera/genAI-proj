FROM python:3.11-slim
WORKDIR /app
# Install ffmpeg for video generation and common build deps
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg build-essential libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app
COPY .env.example .env
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
