# LogiSight — Final Implementation Plan
### CockroachDB × AWS Hackathon Migration
**Backend:** AWS (Lambda + API Gateway, serverless FastAPI via Mangum) · **Frontend:** Vercel · **LLM:** Full Bedrock cutover · **Starting point:** existing repo only (no CockroachDB cluster or AWS account provisioned yet)

---

## 0. Ground Rules for the Code-Gen Agent

- Do not remove existing FastAPI route structure, SQLAlchemy models, or React components unless explicitly listed below — extend, don't rewrite from scratch.
- Every CockroachDB write to a high-contention table (charge mappings, copilot memory events) must be wrapped in retry-on-`40001` (serialization failure) logic. Use SQLAlchemy's built-in retry hook or a decorator — see Section 3.4.
- All AWS credentials/config come from environment variables, never hardcoded. Provide a `.env.example` for local dev and document Lambda environment variables separately.
- Preserve multi-tenancy: every new table (`copilot_sessions`, `copilot_memory_events`, `charge_embeddings`) must include `tenant_id` and respect existing RBAC checks.

---

## 1. Final Architecture

```
Vercel (Frontend)                    AWS (Backend)                       CockroachDB Cloud
─────────────────                    ─────────────                       ─────────────────
React 18 + TS + Vite   ───HTTPS───▶  API Gateway (REST)
                                            │
                                            ▼
                                     Lambda: logisight-api
                                     (FastAPI via Mangum)
                                            │
                        ┌───────────────────┼──────────────────────┐
                        ▼                   ▼                      ▼
                 Amazon Bedrock      CockroachDB MCP Server   Amazon S3
                 (Claude model,      (agent read-access to     (invoice PDFs)
                 Copilot reasoning)   CDB, audited)                  │
                                            │                        ▼
                                            ▼                Lambda: logisight-ingest
                                     CockroachDB Cluster      (S3-triggered, Veryfi OCR
                                     - transactional tables    + embedding generation)
                                     - vector-indexed              │
                                       embeddings          ────────┘
                                     - copilot memory tables  (writes extracted data +
                                                                embeddings into CockroachDB)
```

**Two Lambda functions, one API Gateway, one S3 bucket, one CockroachDB cluster, Bedrock for all LLM calls.**

---

## 2. CockroachDB Schema Additions

Add to the existing SQLAlchemy models (new file: `backend/app/models/copilot_memory.py`):

```python
# copilot_sessions — one row per Copilot conversation
- id: UUID (PK)
- tenant_id: UUID (FK, indexed)
- user_id: UUID (FK)
- started_at: timestamp
- last_active_at: timestamp
- status: enum(active, closed)

# copilot_memory_events — structured memory of what the agent did/decided
- id: UUID (PK)
- session_id: UUID (FK -> copilot_sessions, indexed)
- tenant_id: UUID (indexed)
- event_type: enum(query, tool_call, decision, user_message, agent_message)
- content: JSONB
- created_at: timestamp

# charge_embeddings — vector memory for semantic charge matching
- id: UUID (PK)
- tenant_id: UUID (indexed)
- charge_name: text
- source: enum(charge_master, invoice_line, learned_mapping)
- embedding: VECTOR(1536)   -- match Bedrock embedding model dimension
- created_at: timestamp
```

**Indexing:**
- `CREATE INDEX ON charge_embeddings USING vector_cosine_ops (embedding);` (or CockroachDB's native vector index syntax — confirm exact DDL against current CockroachDB docs at build time, syntax has been evolving)
- Standard secondary indexes on `tenant_id`, `session_id` for the memory tables

**Migration file:** `backend/alembic/versions/xxxx_add_copilot_memory.py` — generate via `alembic revision --autogenerate` after models are added, then hand-check the vector column DDL (Alembic's autogenerate may not know the CockroachDB vector type — write it manually if needed).

---

## 3. Backend Changes (FastAPI)

### 3.1 Database connection
- Replace `DATABASE_URL` (Supabase) with CockroachDB connection string in `backend/app/core/config.py`
- SQLAlchemy engine: use `cockroachdb://` dialect (via `sqlalchemy-cockroachdb` package) or plain `postgresql://` with `sslmode=verify-full` — CockroachDB Cloud requires SSL
- Add `sqlalchemy-cockroachdb` to `requirements.txt`

### 3.2 New dependencies
```
sqlalchemy-cockroachdb
boto3                  # Bedrock + S3 + Lambda
mangum                 # FastAPI -> Lambda adapter
```
Remove or make optional: `openai` (keep only if a fallback path is wanted — user confirmed full cutover, so remove).

### 3.3 Bedrock integration
- New module: `backend/app/services/bedrock_client.py` — wraps `boto3.client("bedrock-runtime")`
- Update LangChain LLM provider in the Copilot service from `ChatOpenAI` to `ChatBedrock` (`langchain-aws` package) pointed at an Anthropic Claude model available on Bedrock
- Update embedding calls (for `charge_embeddings`) to use a Bedrock embedding model (e.g. Titan Embeddings or Cohere via Bedrock) — keep dimension consistent with the vector column defined in Section 2

### 3.4 CockroachDB retry logic
- Add `backend/app/core/db_retry.py`: a decorator/context manager that catches `sqlalchemy.exc.OperationalError` with SQLSTATE `40001` and retries the transaction (exponential backoff, max 3 attempts) — CockroachDB's standard pattern for serializable transactions
- Apply to all write paths touching `charge_master`, `charge_mappings`, `copilot_memory_events`

### 3.5 MCP Server wiring
- The Copilot agent's tool-calling layer should register CockroachDB's Cloud Managed MCP Server as a tool source, pointed at `https://cockroachlabs.cloud/mcp` (per-cluster endpoint from the Cloud Console)
- Scope it read-only (matches the safe-by-default posture) — agent uses it for ad hoc querying during conversation (e.g. "show me anomalies from last week"), while structured writes go through the normal SQLAlchemy models
- Document the MCP config (cluster ID, auth token) as an environment variable, not committed to the repo

### 3.6 Lambda handler for the API
- New file: `backend/lambda_handler.py`
```python
from mangum import Mangum
from app.main import app
handler = Mangum(app)
```
- Package: FastAPI app + dependencies as a Lambda deployment package or container image (container image recommended given LangChain/boto3 size — use AWS Lambda's container support)

### 3.7 Ingestion Lambda (new, separate function)
- New directory: `backend/lambda_ingest/`
- Trigger: S3 `ObjectCreated` event on the invoice-upload bucket
- Logic: fetch PDF from S3 → Veryfi OCR extraction (existing logic, ported from current backend route) → parse charges → generate Bedrock embeddings for each charge line → write extracted invoice + charge rows + embeddings into CockroachDB (with retry logic from 3.4)
- On completion, optionally write a `copilot_memory_events` row (`event_type=tool_call`) so the Copilot "remembers" that a new invoice was processed — this is what makes the pipeline visibly agentic in the demo

### 3.8 Upload flow change
- Frontend invoice upload no longer POSTs the file directly to FastAPI; instead:
  1. Frontend requests a pre-signed S3 upload URL from the API (`POST /invoices/upload-url`)
  2. Frontend uploads PDF directly to S3
  3. S3 event triggers `logisight-ingest` Lambda automatically
  4. Frontend polls or subscribes (simple polling endpoint is fine for hackathon scope) for processing status

---

## 4. Frontend Changes (React + Vite, hosted on Vercel)

- Update `API_BASE_URL` env var to the API Gateway invoke URL
- Update invoice upload component to use the pre-signed URL flow (3.8) instead of direct multipart POST
- Add a simple "processing..." status indicator polling `GET /invoices/{id}/status` after upload — useful for the demo video to visibly show the async Lambda pipeline working
- No framework changes needed; CORS on API Gateway must allow the Vercel domain

---

## 5. Environment Variables Reference

**Backend Lambda (`logisight-api`):**
```
COCKROACHDB_URL=cockroachdb://<user>:<password>@<cluster-host>:26257/<db>?sslmode=verify-full
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-<version>
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2
S3_INVOICE_BUCKET=logisight-invoices-<env>
CDB_MCP_ENDPOINT=https://cockroachlabs.cloud/mcp
CDB_MCP_CLUSTER_ID=<cluster-id>
CDB_MCP_TOKEN=<token>
CORS_ALLOWED_ORIGIN=https://<your-vercel-domain>
```

**Ingest Lambda (`logisight-ingest`):**
```
COCKROACHDB_URL=<same as above>
BEDROCK_REGION=us-east-1
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2
VERYFI_CLIENT_ID=<existing>
VERYFI_CLIENT_SECRET=<existing>
VERYFI_USERNAME=<existing>
VERYFI_API_KEY=<existing>
```

**Frontend (Vercel):**
```
VITE_API_BASE_URL=https://<api-gateway-id>.execute-api.<region>.amazonaws.com/prod
```

---

## 6. CockroachDB Cloud — Step-by-Step Setup

1. **Create account**: go to [cockroachlabs.cloud](https://cockroachlabs.cloud), sign up, verify email.
2. **Create a cluster**: Console → Clusters → Create Cluster → choose **Serverless** (free tier is enough for hackathon judging/demo). Pick a region close to your AWS Lambda region (e.g. `us-east-1`) to minimize latency.
3. **Create a SQL user**: Console → your cluster → SQL Users → Add User. Save the generated password immediately (shown once).
4. **Get the connection string**: Console → your cluster → Connect → select "General connection string" → copy the `cockroachdb://` URL. This is your `COCKROACHDB_URL`.
5. **Create the database**: using `cockroach sql` CLI or the Console SQL shell:
   ```sql
   CREATE DATABASE logisight;
   ```
6. **Enable/confirm vector support**: CockroachDB's vector indexing may require a specific cluster version/feature flag — check the Console's "Distributed Vector Indexing" docs link under your cluster for current enablement steps before writing DDL.
7. **Run migrations**: from `backend/`, with `COCKROACHDB_URL` set:
   ```bash
   alembic upgrade head
   ```
8. **Set up the Managed MCP Server**: Console → your cluster → Integrations (or "Agent Tools") → MCP Server → Generate config. This gives you the per-cluster MCP endpoint + auth token to plug into `CDB_MCP_ENDPOINT` / `CDB_MCP_TOKEN`. Confirm it's set to read-only mode.
9. **(Optional) Agent Skills Repo**: clone CockroachDB's open-source Agent Skills repo if you want the Copilot's tool layer to use pre-built CockroachDB expertise skills rather than hand-written prompts — this can strengthen the "Technical Implementation" judging criterion.
10. **Test the connection** locally before deploying: `psql "$COCKROACHDB_URL"` and run `SELECT 1;`.

---

## 7. AWS — Step-by-Step Setup

### 7.1 Account & CLI
1. Create/use an AWS account, install the AWS CLI, run `aws configure` with an IAM user that has admin access for setup (scope down for production later).

### 7.2 Amazon Bedrock
2. Console → Bedrock → Model access → request access to the Claude model(s) you plan to use and to the Titan (or Cohere) embedding model. Approval is usually instant for Anthropic models but confirm before build day.
3. Note the model IDs shown in the console — these go into `BEDROCK_MODEL_ID` / `BEDROCK_EMBEDDING_MODEL_ID`.

### 7.3 S3
4. Create the invoice bucket:
   ```bash
   aws s3 mb s3://logisight-invoices-hackathon
   ```
5. Enable CORS on the bucket (needed for direct browser → S3 pre-signed uploads) — add a CORS config allowing PUT from your Vercel domain and localhost.
6. Add an **event notification**: S3 bucket → Properties → Event notifications → Create event notification → Event type "All object create events" → Destination: Lambda function `logisight-ingest` (create this Lambda first, see 7.5, then wire the trigger).

### 7.4 IAM Roles
7. Create an execution role for both Lambdas with:
   - `AWSLambdaBasicExecutionRole` (CloudWatch logs)
   - `AmazonBedrockFullAccess` (or a scoped `bedrock:InvokeModel` policy)
   - `AmazonS3ReadOnlyAccess` (ingest Lambda needs to read uploaded PDFs) or scoped to the specific bucket
   - Outbound network access to CockroachDB Cloud (Lambda in a VPC only if you need private connectivity — CockroachDB Serverless is reachable over the public internet with SSL, so a VPC is not required for the hackathon)

### 7.5 Lambda: `logisight-api`
8. Build the container image (recommended, since LangChain + boto3 + Bedrock SDKs are heavy):
   ```bash
   cd backend
   docker build -t logisight-api .
   ```
   Dockerfile should use an AWS Lambda Python base image (`public.ecr.aws/lambda/python:3.11`) and set `CMD ["lambda_handler.handler"]`.
9. Push to ECR:
   ```bash
   aws ecr create-repository --repository-name logisight-api
   aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   docker tag logisight-api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/logisight-api:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/logisight-api:latest
   ```
10. Create the Lambda function from the ECR image (Console or CLI), attach the IAM role from 7.4, set all env vars from Section 5, set timeout to 30s+ (LLM calls can be slow) and memory to at least 1024MB.

### 7.6 API Gateway
11. Create a new REST API (or HTTP API — cheaper, sufficient here) → integrate with `logisight-api` Lambda using proxy integration (`{proxy+}` route, ANY method).
12. Enable CORS on the API Gateway for your Vercel domain.
13. Deploy to a stage (e.g. `prod`) — this gives you the invoke URL for `VITE_API_BASE_URL`.

### 7.7 Lambda: `logisight-ingest`
14. Package similarly (container image, since it also needs boto3 + Veryfi client + embedding calls) or as a plain zip if dependencies are lighter than the API Lambda.
15. Create the function, attach the same IAM role, set env vars from Section 5.
16. Go back to S3 (7.3 step 6) and finish wiring the event notification to this Lambda's ARN. Grant S3 permission to invoke it:
    ```bash
    aws lambda add-permission \
      --function-name logisight-ingest \
      --statement-id s3invoke \
      --action lambda:InvokeFunction \
      --principal s3.amazonaws.com \
      --source-arn arn:aws:s3:::logisight-invoices-hackathon
    ```

### 7.8 End-to-end test
17. Upload a test PDF to S3 manually, confirm `logisight-ingest` fires (CloudWatch Logs), confirm rows land in CockroachDB, confirm the Copilot can answer a question about it via the API Gateway URL.

---

## 8. Vercel — Frontend Deployment

1. Push the repo (with frontend changes from Section 4) to GitHub if not already.
2. In Vercel: New Project → import the repo → set root directory to `frontend/`.
3. Set environment variable `VITE_API_BASE_URL` to the API Gateway invoke URL from 7.6.
4. Deploy. Confirm CORS works end-to-end from the deployed Vercel domain against the API Gateway.

---

## 9. Demo & Submission Checklist

- [ ] CockroachDB cluster live, migrations applied, vector index confirmed working
- [ ] MCP Server connected and used by the Copilot for at least one live query in the demo
- [ ] Charge embeddings populated and semantic match demonstrated (upload an invoice with a slightly-differently-worded charge name, show it gets matched)
- [ ] S3 upload → Lambda ingest → CockroachDB write shown end-to-end
- [ ] Bedrock-powered Copilot answering a natural-language question, citing memory from a past session
- [ ] Frontend live on Vercel, backend live on AWS, both reachable publicly
- [ ] README updated with: architecture diagram, explicit list of CockroachDB tools used + how, explicit list of AWS services used + how, setup instructions
- [ ] <3 min demo video recorded and uploaded (YouTube/Vimeo, public)
- [ ] MIT license confirmed visible in repo's About section

---

## 10. Notes for the Code-Gen Agent

- Confirm exact CockroachDB vector column/index DDL syntax against current docs before generating migration code — this has changed across CockroachDB versions and the plan above uses illustrative syntax.
- Confirm current Bedrock model IDs for Claude and the embedding model at build time (these are periodically updated by AWS).
- Keep the existing role-based access control (Super Admin / Client / Forwarder) enforced on all new endpoints (`/invoices/upload-url`, `/invoices/{id}/status`, Copilot session endpoints).
- Favor small, reviewable PRs in this order: (1) CockroachDB connection + migration, (2) memory tables + retry logic, (3) Bedrock swap, (4) S3 presigned upload flow, (5) ingest Lambda, (6) API Lambda packaging, (7) MCP wiring, (8) frontend polling/status UI.
