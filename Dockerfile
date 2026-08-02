# LogiSight API — Root Dockerfile for Railway
FROM python:3.11-slim

WORKDIR /app

# Install dependencies from the backend folder
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ app/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini .

# Expose port
EXPOSE 8000

# Start the FastAPI application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
