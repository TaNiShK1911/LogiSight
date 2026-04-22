# LogiSight

AI-Powered Freight Audit & Invoice Intelligence Platform

## Overview

LogiSight is a multi-tenant web platform that digitizes the freight audit workflow between Clients (buyers/importers) and Freight Forwarders (carriers). The system automatically maps charge names to the Client's internal Charge Master, compares invoices against quotes, flags anomalies, and provides a natural language Copilot interface.

## Tech Stack

- Frontend: React 18 + TypeScript + Vite
- Backend: Python 3.11 + FastAPI + SQLAlchemy
- Database: Supabase PostgreSQL
- Authentication: Supabase Auth (JWT)
- PDF Extraction: Veryfi OCR API
- AI: LangChain + OpenAI GPT-4o-mini

## Key Features

- Automated charge name mapping with dictionary lookup and aliases
- Human-in-the-loop learning for unmapped charges
- PDF invoice extraction and analysis
- Anomaly detection (amount mismatches, unexpected charges, duplicates)
- Natural language Copilot for freight data queries
- Multi-tenant architecture with role-based access control

## User Roles

- Super Admin: Platform-level management
- Client Admin/User: Manages Charge Master, reviews quotes and invoices
- Forwarder Admin/User: Submits quotes and uploads invoices

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL and SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## License

MIT
