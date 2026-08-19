FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-vollkorn \
    fonts-cabin \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Instalar Chromium para Playwright (browser publisher sin APIs)
RUN playwright install-deps chromium && playwright install chromium

COPY . .

RUN mkdir -p data/chroma publication_queue tmp/images tmp/video

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "cli"]
CMD ["--help"]
