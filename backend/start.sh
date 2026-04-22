#!/bin/bash
# Start LogiSight Backend Server

echo "🚀 Starting LogiSight Backend..."
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    echo "Run: source .venv/bin/activate"
    echo "Or on Windows: .venv\\Scripts\\activate"
    exit 1
fi

# Check critical environment variables
if ! python -c "from dotenv import load_dotenv; load_dotenv(); import os; exit(0 if os.getenv('DATABASE_URL') else 1)" 2>/dev/null; then
    echo "❌ DATABASE_URL not set in .env file"
    exit 1
fi

echo "✓ Environment variables loaded"
echo ""

# Start server
echo "Starting uvicorn on http://localhost:8001"
echo "API docs will be available at http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --port 8001
