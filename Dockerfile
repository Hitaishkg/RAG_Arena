FROM python:3.12-slim

WORKDIR /app

# System deps for pdfplumber + faiss
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download sentence-transformers models at build time (not at runtime)
COPY scripts/preload_models.py scripts/preload_models.py
RUN python scripts/preload_models.py

# Copy source
COPY src/ src/
COPY data/ data/
COPY results/ results/

EXPOSE 8080

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
