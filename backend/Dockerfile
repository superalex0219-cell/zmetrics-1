FROM python:3.11-slim

WORKDIR /app

# System deps: curl for healthcheck; pango + DejaVu fonts for WeasyPrint PDF
# export (REPORT-X) — DejaVu covers Cyrillic.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir ".[dev]"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
