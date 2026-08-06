# LogiSight

**AI-Powered Freight Audit & Invoice Intelligence Platform**

## Overview

LogiSight is a multi-tenant web platform that digitizes the freight audit workflow between Clients (buyers/importers) and Freight Forwarders (carriers). The system automatically maps charge names to the Client's internal Charge Master, compares invoices against quotes, flags anomalies, and provides a natural language Copilot interface.

LogiSight is built on a purely agentic architecture powered by **CockroachDB** (as our persistent, globally distributed memory layer) and **AWS** for serverless execution and foundation models. We built our AI agent to rely entirely on CockroachDB for state, conversational memory, and semantic context.

## 🪳 CockroachDB Integrations

*   **CockroachDB Distributed Vector Indexing:** We store vector embeddings for our `Charge Master` (using CockroachDB's native `VECTOR(1536)` type) to perform high-speed semantic search. When an invoice arrives with an unmapped charge type, the system queries the distributed vector index to map it to standard definitions reliably and fast.
*   **CockroachDB Cloud Managed MCP Server:** Our Copilot AI Agent connects directly to our clusters via the managed MCP Server (`https://cockroachlabs.cloud/mcp`). This gives the agent autonomous, read-only SQL access to query freight data, analyze anomalies, and reason over live transactional data securely.

## ☁️ AWS Integrations

*   **Amazon Bedrock:** We use Anthropic's Claude models (via Amazon Bedrock) as the core engine of our Copilot agent, alongside Titan for generating embeddings for the vector store.
*   **AWS Lambda:** We built a serverless event-driven ingestion pipeline. When a freight forwarder uploads a new invoice, it triggers a Lambda function that extracts the invoice data, maps charges, and writes the structured data to CockroachDB.
*   **Amazon S3:** Used for secure artifact storage of uploaded PDF invoices. S3 `PutObject` events automatically trigger our serverless agentic workflow.

## 🛠 Tech Stack

- **Database / Agentic Memory:** CockroachDB (SQLAlchemy 2.0 + asyncpg)
- **AI Models:** Amazon Bedrock (Claude & Titan) + LangChain
- **Cloud Infrastructure:** AWS Lambda, Amazon S3
- **Backend:** Python 3.11 + FastAPI
- **Frontend:** React 18 + TypeScript + Vite + Vercel
- **PDF Extraction:** Veryfi OCR API

## Key Features

- **Agentic Memory:** Persistent Copilot session histories, memory events, and system states stored natively in CockroachDB.
- **Serverless Ingestion:** Automated invoice extraction running on AWS Lambda.
- **Vector-based Mapping:** Automated charge mapping using CockroachDB distributed vector matching.
- **Natural Language Copilot:** An AI assistant that answers queries regarding quotes, invoices, and anomalies using live SQL execution via MCP. It features:
  - **Same-Session Memory:** Remembers the context of previous questions in the same conversation to smoothly handle follow-up references.
  - **Cross-Session Semantic Recall:** Uses CockroachDB vector indexing on past interactions to automatically pull relevant insights from entirely different sessions for the same tenant.
- **Multi-tenant Architecture:** Role-based access control built from the ground up.

## Setup & Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment Setup
cp .env.example .env
# Required: COCKROACHDB_URL (e.g. cockroachdb://...)
# Required: AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Required: CDB_MCP_ENDPOINT for the Copilot agent

alembic upgrade head
uvicorn app.main:app --reload
```

### AWS Lambda Deployment
```bash
cd backend
python deploy_lambda.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## License

MIT
