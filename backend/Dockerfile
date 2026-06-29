# LogiSight Backend — Dockerfile for Alibaba Cloud ECS deployment
FROM python:3.11-slim

WORKDIR /app

# System dependencies for pdf2image (requires poppler-utils)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default: run FastAPI server
# Override CMD in docker-compose for Celery workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
