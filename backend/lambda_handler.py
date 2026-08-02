"""
AWS Lambda handler for the LogiSight API.
Wraps the FastAPI app with Mangum for Lambda + API Gateway.
For local development, use: uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
"""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
