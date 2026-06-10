FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Torch in a separate layer so Docker caches it across code changes.
# SAM3 via transformers 5.10 requires newer torch float8 dtypes that are absent in torch 2.5/cu121.
RUN pip install --no-cache-dir \
    "torch==2.11.0+cu128" \
    --index-url https://download.pytorch.org/whl/cu128

RUN pip install --no-cache-dir \
    "torchvision==0.26.0+cu128" \
    --index-url https://download.pytorch.org/whl/cu128

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip "setuptools<82" \
    && pip install --no-cache-dir ".[sam3,igev]"

COPY . .

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
