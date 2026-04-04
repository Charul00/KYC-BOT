# ── Backend Dockerfile for Railway ────────────────────────────────────────────
# Uses Python 3.11-slim (stable wheels for chromadb, flashrank, etc.)
# Installs Tesseract OCR for image-based PDF extraction

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create persistent data directories
# Railway volumes should be mounted at /data
RUN mkdir -p /data/chroma_db /data/documents /tmp/flashrank_cache

# Set working directory
WORKDIR /app

# Copy and install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Environment defaults (overridden by Railway env vars)
ENV CHROMA_PERSIST_DIR=/data/chroma_db \
    DOCUMENTS_DIR=/data/documents \
    CHROMA_ANONYMIZED_TELEMETRY=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port (Railway sets $PORT automatically)
EXPOSE 8000

# Start the server — Railway injects $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
