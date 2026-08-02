# LogiSight API — Standard Dockerfile for Railway/Render
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Expose port (Railway provides the PORT environment variable)
EXPOSE 8000

# Start the FastAPI application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
