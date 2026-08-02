"""
Vercel serverless entry point for the FastAPI backend.
Vercel's Python runtime looks for an `app` variable in api/index.py.
"""

from app.main import app
