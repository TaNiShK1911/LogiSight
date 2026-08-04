# LogiSight

**AI-Powered Freight Audit & Invoice Intelligence Platform**

## Overview

LogiSight is a multi-tenant web platform that digitizes the freight audit workflow between Clients (buyers/importers) and Freight Forwarders (carriers). The system automatically maps charge names to the Client's internal Charge Master, compares invoices against quotes, flags anomalies, and provides a natural language Copilot interface.

LogiSight is built on a purely agentic architecture powered by **CockroachDB** (as our persistent, globally distributed memory layer) and **AWS** for serverless execution and foundation models. We built our AI agent to rely entirely on CockroachDB for state, conversational memory, and semantic context.

## 🪳 CockroachDB Integrations

*   **CockroachDB Distributed Vector Indexing:** We store vector embeddings for our `Charge Master` using CockroachDB's native `VECTOR(1536)` type with a distributed vector index (`CREATE VECTOR INDEX`). When an invoice arrives with an unmapped charge type, the system generates an embedding via Amazon Bedrock Titan and queries the vector index using the `<=>` cosine distance operator — all server-side in a single SQL query — to find the closest standard charge definition.
*   **CockroachDB Cloud Managed MCP Server:** Our Copilot AI Agent connects to CockroachDB via the Cloud Managed MCP Server (`https://cockroachlabs.cloud/mcp`) using the Model Context Protocol (JSON-RPC 2.0 over Streamable HTTP). The agent discovers available tools via `tools/list` and executes read-only SQL queries via `tools/call`, providing autonomous data access for answering natural language questions about freight data.

## ☁️ AWS Integrations

*   **Amazon Bedrock:** We use Titan Embeddings (`amazon.titan-embed-text-v2:0`) for generating charge name embeddings stored in the CockroachDB vector index. The Copilot agent uses Groq (LLaMA 3.3 70B) as its primary LLM for fast inference, with Bedrock Claude as a fallback.
*   **AWS Lambda:** We built a serverless event-driven ingestion pipeline. When a freight forwarder uploads a new invoice, it triggers a Lambda function that extracts the invoice data, maps charges, and writes the structured data to CockroachDB.
*   **Amazon S3:** Used for secure artifact storage of uploaded PDF invoices. S3 `PutObject` events automatically trigger our serverless agentic workflow.

## 🛠 Tech Stack

- **Database / Agentic Memory:** CockroachDB (SQLAlchemy 2.0 + asyncpg + native VECTOR type)
- **AI Models:** Groq (LLaMA 3.3 70B primary) + Amazon Bedrock (Claude fallback & Titan Embeddings) + LangChain
- **Cloud Infrastructure:** AWS Lambda, Amazon S3
- **CockroachDB Tools:** Distributed Vector Indexing, Cloud Managed MCP Server
- **Backend:** Python 3.11 + FastAPI
- **Frontend:** React 18 + TypeScript + Vite + Vercel
- **PDF Extraction:** Veryfi OCR API

## Key Features

- **Agentic Memory:** Persistent Copilot session histories, memory events, and system states stored natively in CockroachDB.
- **Serverless Ingestion:** Automated invoice extraction running on AWS Lambda.
- **Vector-based Mapping:** Automated charge mapping using CockroachDB's native `VECTOR(1536)` type with distributed vector indexing and Bedrock Titan embeddings — similarity search runs server-side via the `<=>` cosine distance operator.
- **Natural Language Copilot:** An AI assistant that answers queries regarding quotes, invoices, and anomalies. Optionally routes queries through the CockroachDB Cloud MCP Server when configured, with graceful fallback to direct SQL.
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
# Optional: CDB_MCP_ENDPOINT, CDB_MCP_CLUSTER_ID, CDB_MCP_TOKEN (for MCP Server)

alembic upgrade head

# Backfill charge embeddings (requires AWS Bedrock access)
python -m scripts.backfill_charge_embeddings

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

MIT — see [LICENSE](LICENSE).
