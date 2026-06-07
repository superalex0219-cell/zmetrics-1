FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Torch with CUDA 12.1 in a separate layer so Docker caches it across code changes
RUN pip install --no-cache-dir \
    "torch>=2.3.0" \
    --index-url https://download.pytorch.org/whl/cu121

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir ".[sam3]"

COPY . .

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
