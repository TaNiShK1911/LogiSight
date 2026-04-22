# LogiSight (FreightAuditPro)

**AI-Powered Freight Audit & Invoice Intelligence Platform**

> A multi-tenant web platform that digitizes the freight audit workflow between **Clients** (buyers/importers) and **Freight Forwarders** (carriers). Forwarders submit quotes in their own nomenclature. The system automatically maps charge names to the Client's internal Charge Master using dictionary lookup with aliases, stores everything consistently, compares invoices against quotes, flags anomalies, and surfaces a natural language Copilot on top — all without the Forwarder ever needing to know how the Client organizes their data internally.

---

## The Problem

- Freight invoices arrive as unstructured PDFs with charge names that vary wildly across forwarders — "BAF", "Fuel Levy", "Bunker Adj. Fee", "Fuel Surcharge" all mean the same thing
- Every forwarder uses their own nomenclature; no two are consistent
- Clients need all charge data stored under their own standardized names for clean analysis
- No single place to compare a quote vs invoice at charge level and automatically flag overcharges
- Finance teams cannot get a cost breakdown per shipment on demand
- No duplicate invoice detection or unexpected charge alerting

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + TypeScript + Vite + React Query + React Router |
| **Backend** | Python 3.11 + FastAPI + SQLAlchemy (async) + Alembic |
| **Database** | Supabase PostgreSQL (serverless, shared-schema multi-tenancy) |
| **Authentication** | Supabase Auth (JWT with RS256 verification) |
| **PDF Extraction** | Veryfi OCR API (purpose-built freight invoice extraction) |
| **Charge Mapping** | Dictionary lookup with aliases + Human-in-the-loop learning |
| **Copilot** | LangChain SQL Agent + OpenAI GPT-4o-mini |
| **Deployment** | Railway (backend) + Vercel (frontend) |

---

## User Roles

| Role | Description |
|---|---|
| **Super Admin** | Platform-level. Creates companies and their first admin user via Supabase Admin API. Activates / deactivates companies. |
| **Client Admin / User** | Belongs to a buyer company. Manages the Charge Master and its aliases. Views quotes from forwarders in their own nomenclature. Accepts or rejects quotes with an optional note. Triggers invoice analysis. Reviews and corrects unmapped charge mappings (human-in-the-loop). |
| **Forwarder Admin / User** | Belongs to a carrier company. Submits quotes in their own terminology via a form. Uploads invoice PDFs against accepted quotes. Sees quote status and rejection notes. Never sees the Client's Charge Master or any mapping logic. |

---

## What is the Charge Master?

Each Client company maintains its own **Charge Master** — a private, internal list of standardized charge names, short codes, and aliases. It is never exposed to Forwarders.

| Short Name | Full Name | Example Aliases |
|---|---|---|
| BAF | Bunker Adjustment Factor | fuel surcharge, fuel levy, bunker surcharge, bunker adj fee, fuel adj |
| CAF | Currency Adjustment Factor | currency surcharge, forex adjustment, currency levy |
| THC | Terminal Handling Charge | port handling, terminal fee, handling fee, port dues |
| DEM | Demurrage | detention charge, demurrage fee, storage fee |
| XRC | X-ray / Security Screening | security surcharge, x-ray fee, screening charge |

Aliases are populated by:
1. **Client input** — Client adds aliases manually when creating Charge Master entries
2. **Learned** — whenever a Client manually corrects an unmapped charge in the UI, that correction is automatically saved as a new alias on the relevant Charge Master entry

---

## Core Concept: Charge Mapping with Human-in-the-Loop

Every time a Forwarder submits a charge name — whether in a quote or an invoice — the system maps it to the Client's Charge Master:

```
Raw charge name from Forwarder (e.g. "Fuel Levy")
        │
        ▼
Dictionary Lookup (case-insensitive)
        Check Charge Master: name, short_name, and all aliases
        "fuel levy" → matches alias of BAF → MAPPED ✅
        No match found? → UNMAPPED 🔴
        │
        ▼
Human-in-the-Loop (if unmapped)
        Client sees unmapped charge in UI
        Client manually assigns to correct Charge Master entry
        System automatically saves as new alias
        Future submissions with same name → auto-mapped ✅
```

**Mapping Tiers:**
- `DICTIONARY` — Matched via alias lookup (automatic)
- `HUMAN` — Manually corrected by client (learned)
- `UNMAPPED` — No match found, needs human review

**Why this approach?**
Simple, transparent, and learns from corrections. No complex ML models needed — the system gets smarter with each manual correction.

---

## Confidence Indicators in the UI

| Badge | Source | Meaning |
|---|---|---|
| 🟢 Green | DICTIONARY | Matched via alias — no action needed |
| 🟡 Amber | HUMAN | Previously corrected by client — review if needed |
| 🔴 Red | UNMAPPED | Needs human review and manual mapping |

---

## User Flow

### 1. Platform Setup (Super Admin)
- Super Admin creates a Client company and a Forwarder company on the platform
- Each company gets an Admin user who manages their own team
- Client Admin sets up their **Charge Master** with full names, short codes, and known aliases
- The Charge Master is internal — Forwarders never see it

### 2. Quote Submission (Forwarder)
- Forwarder logs in and fills out a structured **Quote Form**
- Selects which **Client company** the quote is addressed to
- Fills shipment details: origin airport, destination airport, AWB / tracking number, gross weight, volumetric weight, chargeable weight, currency
- Adds charge lines in **their own terminology** — they type charge names freely as they know them
- Each charge line includes: raw charge name, rate, basis (Per KG / Per Shipment / Per CBM), quantity, amount
- Submits the quote — it is immediately visible to the addressed Client

### 3. Automated Quote Mapping (System)
- Dictionary lookup runs on every charge line against the Client's Charge Master and aliases
- Each charge is stored with both its **raw name** (exactly what the Forwarder wrote) and its **mapped Charge Master entry**
- Unmapped charges are flagged `UNMAPPED` and queued for Client review

### 4. Quote Review (Client)
- Client sees all incoming quotes in their dashboard
- Charge names are displayed in **Client's own Charge Master nomenclature** — the Forwarder's raw names are shown alongside for reference
- Low-confidence and unresolved mappings are highlighted for manual correction; corrections are saved as aliases automatically
- Client **Accepts** or **Rejects** the quote with an optional note
- On **acceptance**: quote charges are locked under Charge Master nomenclature; status → `ACCEPTED`
- On **rejection**: quote is terminal — Forwarder sees the status and rejection note (raw names only, never Charge Master names)

### 5. Invoice Upload (Forwarder)
- After shipment delivery, the Forwarder uploads the **freight invoice as a PDF** against an accepted quote, matched by AWB / tracking number

### 6. Automated Invoice Extraction & Mapping (System)
- **Extraction — Veryfi OCR API:** Purpose-built for freight and logistics invoice extraction. Handles both digital and scanned PDFs reliably
- Extracted raw charge names pass through the same dictionary lookup with aliases
- By this point the Charge Master has aliases learned from quote mapping, so invoice mapping accuracy is higher than cold-start

### 7. Invoice Analysis (Client)
- Client views the uploaded invoice in their own Charge Master nomenclature
- Client clicks **"Analyse"** — the anomaly detection engine compares every invoice charge against the corresponding quote charge (matched via Charge Master IDs)
- Results displayed as a charge-level comparison table with all flags clearly marked

### 8. Anomaly Flags

| Flag | Meaning |
|---|---|
| `AMOUNT_MISMATCH` | Invoice amount for a charge differs from the quoted amount beyond the configured threshold |
| `RATE_MISMATCH` | Per-unit rate changed between quote and invoice |
| `BASIS_MISMATCH` | Charging basis changed — e.g. quote said "Per KG", invoice says "Per Shipment" |
| `UNEXPECTED_CHARGE` | Charge appears on invoice but was not present in the accepted quote |
| `MISSING_CHARGE` | Charge was in the quote but is absent from the invoice |
| `DUPLICATE_INVOICE` | Same invoice number already exists for this Client |

### 9. Logistics Copilot (Client)
- A chat interface where Client users ask plain English questions about their freight data
- Powered by a LangChain SQL Agent with gpt-4o-mini — translates natural language to SQL, executes it scoped strictly to the Client's company, returns a plain English answer
- All data is normalised to Charge Master nomenclature, so answers are consistent and aggregations are accurate

**Example queries:**
- "Which forwarder had the most anomalies this month?"
- "What is our total invoice amount vs quoted amount across all accepted quotes in 2026?"
- "Show me all invoices with unexpected charges in Q1"
- "Which charge type has the highest average variance across all forwarders?"
- "Which forwarder has been most consistent with their quotes?"
- "What was our total overpayment on BAF charges last quarter?"

---

## Architecture

### Multi-Tenancy
All companies share a single Supabase PostgreSQL database. Data isolation is enforced at the application layer — every FastAPI endpoint extracts `company_id` from the JWT token and scopes all queries with it. No cross-company data leakage is possible.

### Data Visibility Rules

| Data | Forwarder sees | Client sees |
|---|---|---|
| Quote charge names | Their own raw names only | Mapped Charge Master names + raw names for reference |
| Quote status & rejection note | Yes (raw names in note, never Charge Master names) | Yes |
| Charge Master | Never | Full access |
| Mapping confidence scores | Never | Yes |
| Invoice charge names | Their own raw names | Mapped Charge Master names + raw names |
| Anomaly results | Never | Yes |
| Other companies' data | Never | Never |

### System Flow

```
Forwarder submits Quote Form (own terminology, selects target Client)
        ↓
Dictionary lookup: Check Charge Master names, short_names, and all aliases
        ↓
Quote stored: raw names + mapped Charge Master IDs + mapping tier
        ↓
Client reviews quote in their own nomenclature → Accepts or Rejects
        ↓
Forwarder uploads Invoice PDF against accepted quote (matched by AWB)
        ↓
PDF extracted: Veryfi OCR API
        ↓
Same dictionary lookup on extracted charge names
        ↓
Client clicks "Analyse" → Anomaly detection at Charge Master level
        ↓
Audit dashboard: charge-level comparison + anomaly flags
        ↓
Copilot: natural language queries over all normalised shipment data
```

### API Surface

```
AUTH
  POST   /auth/login                       → JWT token

COMPANIES & USERS (Super Admin)
  POST   /companies                        → create company + first admin
  GET    /companies                        → list all companies
  PATCH  /companies/{id}/status            → activate / deactivate
  POST   /companies/{id}/users             → add user to company
  PATCH  /users/{id}/admin                 → promote / demote admin

MASTER DATA
  GET / POST / PATCH  /masters/countries
  GET / POST / PATCH  /masters/currencies
  GET / POST / PATCH  /masters/airports
  GET / POST / PATCH  /masters/charges     → Charge Master, scoped to JWT company_id
  POST               /masters/charges/{id}/aliases  → add alias to a Charge Master entry

QUOTES
  POST   /quotes                           → forwarder submits quote (triggers mapping pipeline)
  GET    /quotes                           → list (filtered by company + role)
  GET    /quotes/{id}                      → detail with raw + mapped charge lines
  PATCH  /quotes/{id}/status               → client accepts or rejects with optional note

MAPPING CORRECTIONS
  PATCH  /quotes/charges/{id}/mapping      → client corrects a quote charge mapping
  PATCH  /invoices/charges/{id}/mapping    → client corrects an invoice charge mapping
  (both endpoints auto-save the correction as a new Charge Master alias)

INVOICES
  POST   /invoices/upload                  → multipart: quote_id + PDF file
                                              extracts, maps, stores charges
                                              returns preview of mapped charge lines
  GET    /invoices?quote_id=X              → list invoices for a quote
  GET    /invoices/{id}                    → invoice detail with raw + mapped charges
  POST   /invoices/{id}/analyze            → runs anomaly detection, returns flags
  GET    /invoices/{id}/anomalies          → retrieve stored anomaly results

TRACKING
  GET    /tracking                         → all shipments with current status
  GET    /tracking/{quote_id}/events       → full event history for a shipment

COPILOT
  POST   /copilot/query                    → natural language → SQL → plain English answer
```

---

## Database Schema

```sql
companies
  id, name, short_name, type ('client' | 'forwarder'), address, city, country, is_active

users
  id, company_id, name, email, password_hash, is_admin, is_active

countries        id, name, short_name, is_active
currencies       id, name, short_name, is_active
airports         id, name, iata_code, country_id, is_active

-- Charge Master: private to each Client company
charges
  id, company_id, name, short_name, is_active
  UNIQUE(company_id, name), UNIQUE(company_id, short_name)

-- Aliases per Charge Master entry (used for dictionary lookup)
charge_aliases
  id, charge_id, alias
  UNIQUE(charge_id, alias)

-- Quotes submitted by Forwarder in their own terminology
quotes
  id, forwarder_id, buyer_id, quote_ref, origin_airport_id, destination_airport_id,
  tracking_number, gross_weight, volumetric_weight, chargeable_weight, currency_id,
  status ('SUBMITTED' | 'ACCEPTED' | 'REJECTED'), rejection_note, created_at

-- Quote charge lines: raw Forwarder input + system mapping result
quote_charges
  id, quote_id,
  raw_charge_name,        -- exactly what the Forwarder typed
  mapped_charge_id,       -- FK → charges; NULL if unmapped
  mapped_charge_name,     -- denormalised for display speed
  mapping_tier,           -- 'DICTIONARY' | 'HUMAN' | 'UNMAPPED'
  rate, basis, qty, amount

-- Invoices uploaded by Forwarder
invoices
  id, quote_id, invoice_number, invoice_date, file_path, uploaded_at

-- Extracted + mapped invoice charge lines
invoice_charges
  id, invoice_id,
  raw_charge_name,        -- exactly as extracted from PDF
  mapped_charge_id,       -- FK → charges; NULL if unmapped
  mapped_charge_name,
  mapping_tier,           -- 'DICTIONARY' | 'HUMAN' | 'UNMAPPED'
  rate, basis, qty, amount

-- Anomaly flags from invoice analysis
anomalies
  id, invoice_id, invoice_charge_id, flag_type, description, variance

-- Shipment tracking events
tracking_events
  id, quote_id, event_time, location, status, description
```

---

## Key Design Decisions

**Why does the Forwarder type charge names freely instead of selecting from the Client's Charge Master?**
Forwarders work with many Clients and use their own internal terminology consistently across all of them. Forcing them to learn and use each Client's Charge Master is an unacceptable operational burden. The mapping responsibility belongs entirely to the platform.

**Why dictionary lookup with human-in-the-loop instead of ML models?**
Simple, transparent, and learns from corrections. No complex ML models, embeddings, or LLM calls needed. The system gets smarter with each manual correction as aliases are automatically saved. This approach is deterministic, fast, and cost-effective.

**Why save human corrections as aliases automatically?**
Each correction is a signal about how a specific Forwarder names a specific charge. Storing it as an alias means the dictionary catches it on every future submission — the system improves passively without any retraining.

**Why Veryfi OCR API for extraction?**
Veryfi is purpose-built for freight and logistics documents and handles both digital and scanned PDFs out of the box, significantly outperforming generic extraction on real-world invoice formats.

**Why Text-to-SQL for the Copilot rather than RAG?**
All data is already fully structured and normalised against Charge Master IDs. The questions Clients ask — totals, comparisons, rankings, variance summaries — are exactly what SQL handles with precision. RAG introduces approximate retrieval over data that is already perfectly queryable.

**Why shared database with row-level isolation?**
One connection string, one migration run, trivial Super Admin analytics. Separate databases per company would require dynamic connection routing and per-company connection pools with no user-visible benefit.

---

## Team & Task Ownership

| Member | Domain |
|---|---|
| **Manan** | Mock data — generates realistic freight invoice PDFs using fpdf2 across 3 forwarder naming styles |
| **Tanishk** | Backend Foundation — DB models, migrations, auth, companies, master data, tracking |
| **Kaushik** | Backend Intelligence — charge mapping pipeline, PDF extraction, anomaly detection, quotes & invoices API |
| **Yogesh** | Frontend — all React pages, components, API integration, Copilot UI + backend Copilot service |

## Detailed Task Breakdowns

### FreightAuditPro — Tanishk's Task README
#### Domain: Backend Foundation

You own the entire backend foundation layer. Every other backend developer (Kaushik) and the frontend developer (Yogesh) depend on your models and migrations being ready first. **Your work is the critical path — complete Phase 1 before anything else merges.**

---

#### Your Branch

```bash
git checkout -b feat/tanishk-foundation
```

**PR target:** `dev` (never `main` directly)

---

#### Files You Own — Touch Only These

```
backend/
├── app/
│   ├── main.py                   ← app bootstrap, CORS, router registration
│   ├── models.py                 ← ALL SQLAlchemy ORM models
│   ├── schemas.py                ← ALL Pydantic request/response schemas
│   ├── dependencies.py           ← shared FastAPI dependency injections (get_db, get_current_user)
│   ├── routers/
│   │   ├── auth.py               ← login, token
│   │   ├── companies.py          ← company + user management (Super Admin)
│   │   ├── masters.py            ← countries, currencies, airports, Charge Master, aliases
│   │   └── tracking.py           ← shipment tracking events
│   └── services/
│       └── tracking.py           ← tracking business logic
├── alembic/                      ← all migrations
│   ├── env.py
│   └── versions/
├── alembic.ini
├── requirements.txt
└── .env.example
```

**Do NOT touch:**
- `routers/quotes.py`, `routers/invoices.py`, `routers/copilot.py`
- `services/charge_mapper.py`, `services/synonym_dict.py`, `services/extractor.py`, `services/anomaly.py`, `services/copilot.py`
- Anything under `frontend/`

---

#### Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in: DATABASE_URL, SECRET_KEY (leave Veryfi and OpenAI blank for now)
alembic upgrade head
uvicorn app.main:app --reload
```

Test the API is live:
```bash
curl http://localhost:8000/docs     # Swagger UI should open
```

---

#### Phase 1 — Database Models & Migrations ⚡ CRITICAL PATH

Complete this first. Kaushik and Yogesh cannot start meaningful work until the schema is merged.

##### Task 1.1 — Write all SQLAlchemy ORM models in `app/models.py`

Implement the following models (async-compatible with `sqlalchemy.ext.asyncio`):

```python
# All models use Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id: int (PK)
    name: str (unique)
    short_name: str (unique)
    type: str  # 'client' | 'forwarder'
    address: str (nullable)
    city: str (nullable)
    country: str (nullable)
    is_active: bool (default True)

class User(Base):
    __tablename__ = "users"
    id: int (PK)
    company_id: int (FK → companies.id)
    name: str
    email: str (unique)
    password_hash: str
    is_admin: bool (default False)
    is_active: bool (default True)

class Country(Base):
    __tablename__ = "countries"
    id: int (PK), name: str, short_name: str, is_active: bool

class Currency(Base):
    __tablename__ = "currencies"
    id: int (PK), name: str, short_name: str, is_active: bool

class Airport(Base):
    __tablename__ = "airports"
    id: int (PK), name: str, iata_code: str (unique), country_id: int (FK), is_active: bool

class Charge(Base):
    __tablename__ = "charges"
    id: int (PK)
    company_id: int (FK → companies.id)
    name: str
    short_name: str
    is_active: bool (default True)
    # UNIQUE(company_id, name), UNIQUE(company_id, short_name)
    aliases: relationship → ChargeAlias

class ChargeAlias(Base):
    __tablename__ = "charge_aliases"
    id: int (PK)
    charge_id: int (FK → charges.id, cascade delete)
    alias: str
    # UNIQUE(charge_id, alias)

class Quote(Base):
    __tablename__ = "quotes"
    id: int (PK)
    forwarder_id: int (FK → companies.id)
    buyer_id: int (FK → companies.id)
    quote_ref: str (nullable)
    origin_airport_id: int (FK → airports.id)
    destination_airport_id: int (FK → airports.id)
    tracking_number: str
    gross_weight: float
    volumetric_weight: float
    chargeable_weight: float
    currency_id: int (FK → currencies.id)
    status: str  # 'SUBMITTED' | 'ACCEPTED' | 'REJECTED'
    rejection_note: str (nullable)
    created_at: datetime (default utcnow)

class QuoteCharge(Base):
    __tablename__ = "quote_charges"
    id: int (PK)
    quote_id: int (FK → quotes.id, cascade delete)
    raw_charge_name: str
    mapped_charge_id: int (FK → charges.id, nullable)
    mapped_charge_name: str (nullable)
    mapping_tier: str  # 'DICTIONARY' | 'HUMAN' | 'UNMAPPED'
    rate: float
    basis: str  # 'PER_KG' | 'PER_SHIPMENT' | 'PER_CBM'
    qty: float
    amount: float

class Invoice(Base):
    __tablename__ = "invoices"
    id: int (PK)
    quote_id: int (FK → quotes.id)
    invoice_number: str
    invoice_date: date (nullable)
    file_path: str
    uploaded_at: datetime (default utcnow)

class InvoiceCharge(Base):
    __tablename__ = "invoice_charges"
    id: int (PK)
    invoice_id: int (FK → invoices.id, cascade delete)
    raw_charge_name: str
    mapped_charge_id: int (FK → charges.id, nullable)
    mapped_charge_name: str (nullable)
    mapping_tier: str  # 'DICTIONARY' | 'HUMAN' | 'UNMAPPED'
    rate: float
    basis: str
    qty: float
    amount: float

class Anomaly(Base):
    __tablename__ = "anomalies"
    id: int (PK)
    invoice_id: int (FK → invoices.id, cascade delete)
    invoice_charge_id: int (FK → invoice_charges.id, nullable)
    flag_type: str  # 'AMOUNT_MISMATCH' | 'RATE_MISMATCH' | 'BASIS_MISMATCH' |
                    # 'UNEXPECTED_CHARGE' | 'MISSING_CHARGE' | 'DUPLICATE_INVOICE'
    description: str (nullable)
    variance: float (nullable)

class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    id: int (PK)
    quote_id: int (FK → quotes.id)
    event_time: datetime
    location: str (nullable)
    status: str
    description: str (nullable)
```

##### Task 1.2 — Alembic migration

```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

Verify all tables exist in Neon console before declaring done.

##### Task 1.3 — Write Pydantic schemas in `app/schemas.py`

One `Base`, `Create`, and `Read` schema per model. Key ones:

- `CompanyCreate`, `CompanyRead`
- `UserCreate`, `UserRead`
- `ChargeCreate`, `ChargeRead` (include `aliases: list[str]`)
- `QuoteCreate` (includes `charges: list[QuoteChargeCreate]`), `QuoteRead`
- `QuoteChargeRead` (includes `mapping_tier`)
- `InvoiceRead`, `InvoiceChargeRead`
- `AnomalyRead`
- `TrackingEventRead`
- `TokenResponse` (for auth)

---

#### Phase 2 — Auth & User Management

##### Task 2.1 — `app/dependencies.py`

```python
# Implement these two dependencies used by all routers:

async def get_db() -> AsyncSession:
    # yields async DB session

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    # decodes JWT, loads user from DB, raises 401 if invalid
    # attach company_id to user for downstream scoping
```

Use `python-jose` for JWT, `passlib[bcrypt]` for password hashing. JWT payload must include `user_id`, `company_id`, `is_admin`, `company_type`.

##### Task 2.2 — `routers/auth.py`

```
POST /auth/login
  Body: { email, password }
  Returns: { access_token, token_type: "bearer", user: UserRead }
```

##### Task 2.3 — `routers/companies.py`

All endpoints require Super Admin (enforce with a dependency).

```
POST   /companies                  → create company + first admin user
GET    /companies                  → list all (with is_active filter)
PATCH  /companies/{id}/status      → toggle is_active
POST   /companies/{id}/users       → add a new user to a company
PATCH  /users/{id}/admin           → toggle is_admin
```

---

#### Phase 3 — Master Data

##### Task 3.1 — `routers/masters.py`

Standard CRUD for lookup tables (Countries, Currencies, Airports). Only Super Admin can create/update; all authenticated users can read.

```
GET / POST / PATCH  /masters/countries
GET / POST / PATCH  /masters/currencies
GET / POST / PATCH  /masters/airports
```

##### Task 3.2 — Charge Master endpoints (in `routers/masters.py`)

Scoped to `company_id` from JWT — a Client never sees another Client's charges.

```
GET    /masters/charges            → list all charges for caller's company
POST   /masters/charges            → create a new charge (Client Admin only)
PATCH  /masters/charges/{id}       → update name / short_name / is_active
POST   /masters/charges/{id}/aliases  → add an alias to a charge entry
DELETE /masters/charges/{id}/aliases/{alias_id}
```

---

#### Phase 4 — Tracking

##### Task 4.1 — `services/tracking.py`

```python
async def get_all_shipments(db, company_id) -> list[Quote]:
    # Returns all quotes (shipments) scoped to the company
    # Attaches latest TrackingEvent status to each

async def get_shipment_events(db, quote_id, company_id) -> list[TrackingEvent]:
    # Returns all events for a quote, scoped by company ownership
```

##### Task 4.2 — `routers/tracking.py`

```
GET  /tracking                     → list all shipments with latest status
GET  /tracking/{quote_id}/events   → full event history for one shipment
```

---

#### Phase 5 — App Bootstrap

##### Task 5.1 — `app/main.py`

```python
app = FastAPI(title="FreightAuditPro API")

# CORS: allow frontend origin (localhost:5173 + production Vercel URL)
app.add_middleware(CORSMiddleware, ...)

# Register routers
app.include_router(auth_router, prefix="/auth")
app.include_router(companies_router, prefix="")
app.include_router(masters_router, prefix="/masters")
app.include_router(quotes_router, prefix="/quotes")        # Kaushik implements
app.include_router(invoices_router, prefix="/invoices")    # Kaushik implements
app.include_router(tracking_router, prefix="/tracking")
app.include_router(copilot_router, prefix="/copilot")      # Yogesh implements

@app.get("/health")
async def health(): return {"status": "ok"}
```

Create stub files for routers you don't own (just `router = APIRouter()`) so the app starts without errors while others are building.

---

#### Seeding

Write a `scripts/seed.py` that:
1. Creates Super Admin user (email: `admin@freightauditpro.com`, password: `admin123`)
2. Creates one sample Client company and one sample Forwarder company
3. Seeds countries, currencies, and 10 common airports (JFK, LHR, DXB, SIN, HKG, BOM, LAX, FRA, NRT, SYD)
4. Seeds the sample Client's Charge Master with: BAF, CAF, THC, DEM, XRC + their common aliases

```bash
python scripts/seed.py
```

---

#### Acceptance Criteria

- [ ] `alembic upgrade head` runs clean from a fresh DB
- [ ] `POST /auth/login` returns a valid JWT
- [ ] `GET /masters/charges` returns only the caller's company charges (not other companies')
- [ ] Super Admin can create a company; non-admins get 403
- [ ] All 5 Charge Master entries with aliases are seeded and retrievable
- [ ] `GET /tracking` returns empty list (no data yet) with 200

---

#### Dependencies to Communicate

Once your models.py is finalised (Task 1.1), post the final field list in the group chat. Kaushik's charge mapper and Yogesh's API client both depend on the exact field names you define. Do not rename fields after this point without team consensus.


### FreightAuditPro — Kaushik's Task README
#### Domain: Backend Intelligence (AI Pipeline, PDF Extraction, Anomaly Detection)

You own everything that makes FreightAuditPro intelligent — the charge mapping with dictionary lookup, PDF extraction, anomaly detection, and the quotes & invoices API surface. This is the core product differentiator.

**Prerequisite:** Wait for Tanishk to merge `models.py` and `schemas.py` (Phase 1) before wiring up DB calls. You can build and test the mapping logic in isolation (no DB needed) while Tanishk finishes the schema.

---

#### Your Branch

```bash
git checkout -b feat/kaushik-intelligence
```

**PR target:** `dev` (never `main` directly)

---

#### Files You Own — Touch Only These

```
backend/
├── app/
│   ├── routers/
│   │   ├── quotes.py             ← quote submission + review API
│   │   └── invoices.py           ← invoice upload + analysis API
│   └── services/
│       ├── charge_mapping.py     ← dictionary lookup with aliases (core intelligence)
│       ├── invoice_extraction.py ← Veryfi OCR integration
│       └── anomaly.py            ← anomaly detection engine
└── uploads/                      ← invoice PDF storage directory (create this)
```

**Do NOT touch:**
- `models.py`, `schemas.py`, `dependencies.py` — those are Tanishk's
- `routers/auth.py`, `routers/companies.py`, `routers/masters.py`, `routers/tracking.py` — Tanishk's
- `routers/copilot.py`, `services/copilot.py` — Yogesh's
- Anything under `frontend/`

---

#### Setup

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
# Add to requirements.txt if not already there:
# veryfi>=3.0.0
```

Add to `.env`:
```
VERYFI_CLIENT_ID=your-client-id
VERYFI_CLIENT_SECRET=your-client-secret
VERYFI_USERNAME=your-username
VERYFI_API_KEY=your-api-key
```

---

#### Phase 1 — Charge Mapping with Dictionary Lookup

##### Task 1.1 — `services/charge_mapping.py`

This is the core mapping logic. It performs case-insensitive dictionary lookup against the Charge Master.

```python
# services/charge_mapping.py

async def resolve_raw_charge_name(
    db: AsyncSession,
    raw_name: str,
    buyer_company_id: int,
) -> tuple[int | None, str | None, str]:
    """
    Maps a raw charge name to the buyer's Charge Master.
    Returns: (charge_id, charge_name, tier)
    
    Tier values: 'DICTIONARY', 'HUMAN', 'UNMAPPED'
    """
    raw_l = raw_name.strip().lower()
    
    # Check Charge Master: name, short_name, and all aliases
    result = await db.execute(
        select(Charge)
        .where(Charge.company_id == buyer_company_id)
        .where(Charge.is_active == True)
    )
    charges = result.scalars().all()
    
    for charge in charges:
        # Check name and short_name
        if charge.name.lower() == raw_l or charge.short_name.lower() == raw_l:
            return charge.id, charge.name, "DICTIONARY"
        
        # Check aliases
        for alias in charge.aliases:
            if alias.alias.lower() == raw_l:
                return charge.id, charge.name, "DICTIONARY"
    
    # No match found
    return None, None, "UNMAPPED"
```

**Tests to write:**
- `"fuel surcharge"` with matching alias → maps to BAF
- `"BAF"` exact match on short_name → maps to BAF
- `"Unknown Charge"` with no match → returns UNMAPPED
- Case insensitivity: `"FUEL SURCHARGE"` → maps to BAF

---

#### Phase 2 — PDF Extraction

#### Phase 2 — PDF Extraction

##### Task 2.1 — `services/invoice_extraction.py`

```python
# services/invoice_extraction.py
# Veryfi OCR API for invoice extraction

import veryfi

@dataclass
class ExtractedCharge:
    raw_charge_name: str
    rate: float | None
    basis: str | None   # normalise to 'PER_KG' | 'PER_SHIPMENT' | 'PER_CBM'
    qty: float | None
    amount: float | None

async def extract_invoice_with_veryfi(file_path: str) -> tuple[str, list[ExtractedCharge]]:
    """
    Returns (invoice_number, list_of_extracted_charges).
    Uses Veryfi OCR API for extraction.
    """
    client = veryfi.Client(
        client_id=settings.VERYFI_CLIENT_ID,
        client_secret=settings.VERYFI_CLIENT_SECRET,
        username=settings.VERYFI_USERNAME,
        api_key=settings.VERYFI_API_KEY,
    )
    
    # Process document
    result = client.process_document(file_path)
    
    # Parse Veryfi's line_items into ExtractedCharge list
    charges = []
    for item in result.get("line_items", []):
        charges.append(ExtractedCharge(
            raw_charge_name=item.get("description", "Unknown"),
            rate=item.get("unit_price"),
            basis=normalise_basis(item.get("unit_of_measure")),
            qty=item.get("quantity"),
            amount=item.get("total"),
        ))
    
    invoice_number = result.get("invoice_number", "")
    return invoice_number, charges

def normalise_basis(raw: str | None) -> str:
    """Normalise various basis strings to canonical values."""
    if not raw:
        return "PER_SHIPMENT"
    r = raw.upper()
    if "KG" in r or "WEIGHT" in r:
        return "PER_KG"
    if "CBM" in r or "VOLUME" in r:
        return "PER_CBM"
    return "PER_SHIPMENT"
```

---

#### Phase 3 — Anomaly Detection

##### Task 3.1 — `services/anomaly.py`

```python
# services/anomaly.py

AMOUNT_THRESHOLD_PCT = 0.01   # 1% tolerance

def detect_anomalies(
    invoice_charges: list[InvoiceCharge],
    quote_charges: list[QuoteCharge],
    invoice_id: int,
    existing_invoice_numbers: list[str],
    current_invoice_number: str,
) -> list[AnomalyCreate]:
    """
    Compares invoice charges against quote charges by mapped_charge_id.
    Returns a list of anomaly records to insert.
    """
    anomalies = []

    # DUPLICATE_INVOICE check
    if current_invoice_number in existing_invoice_numbers:
        anomalies.append(AnomalyCreate(
            invoice_id=invoice_id,
            flag_type="DUPLICATE_INVOICE",
            description=f"Invoice {current_invoice_number} already exists",
        ))

    # Build lookup by mapped_charge_id
    quote_by_charge = {qc.mapped_charge_id: qc for qc in quote_charges if qc.mapped_charge_id}
    invoice_by_charge = {ic.mapped_charge_id: ic for ic in invoice_charges if ic.mapped_charge_id}

    # UNEXPECTED_CHARGE: in invoice but not in quote
    for charge_id, ic in invoice_by_charge.items():
        if charge_id not in quote_by_charge:
            anomalies.append(AnomalyCreate(
                invoice_id=invoice_id,
                invoice_charge_id=ic.id,
                flag_type="UNEXPECTED_CHARGE",
                description=f"{ic.mapped_charge_name} was not in the accepted quote",
            ))

    # MISSING_CHARGE: in quote but not in invoice
    for charge_id, qc in quote_by_charge.items():
        if charge_id not in invoice_by_charge:
            anomalies.append(AnomalyCreate(
                invoice_id=invoice_id,
                flag_type="MISSING_CHARGE",
                description=f"{qc.mapped_charge_name} present in quote but absent from invoice",
            ))

    # Per-charge comparisons for charges present in both
    for charge_id in quote_by_charge.keys() & invoice_by_charge.keys():
        qc, ic = quote_by_charge[charge_id], invoice_by_charge[charge_id]

        # BASIS_MISMATCH
        if qc.basis != ic.basis:
            anomalies.append(AnomalyCreate(
                invoice_id=invoice_id, invoice_charge_id=ic.id,
                flag_type="BASIS_MISMATCH",
                description=f"Basis changed from {qc.basis} to {ic.basis}",
            ))

        # RATE_MISMATCH
        if qc.rate and ic.rate and abs(qc.rate - ic.rate) > 0.001:
            anomalies.append(AnomalyCreate(
                invoice_id=invoice_id, invoice_charge_id=ic.id,
                flag_type="RATE_MISMATCH",
                description=f"Rate changed from {qc.rate} to {ic.rate}",
                variance=ic.rate - qc.rate,
            ))

        # AMOUNT_MISMATCH
        if qc.amount and ic.amount:
            diff_pct = abs(ic.amount - qc.amount) / qc.amount
            if diff_pct > AMOUNT_THRESHOLD_PCT:
                anomalies.append(AnomalyCreate(
                    invoice_id=invoice_id, invoice_charge_id=ic.id,
                    flag_type="AMOUNT_MISMATCH",
                    description=f"Amount {ic.amount} differs from quoted {qc.amount}",
                    variance=ic.amount - qc.amount,
                ))

    return anomalies
```

---

#### Phase 4 — Quotes API

##### Task 4.1 — `routers/quotes.py`

```
POST   /quotes
  Auth: Forwarder
  Body: QuoteCreate (with charges list)
  Action:
    1. Load buyer's Charge Master from DB
    2. Run resolve_raw_charge_name() on all charge names
    3. Insert Quote + QuoteCharge rows (with mapping results)
    4. Return QuoteRead with mapped charges

GET    /quotes
  Auth: Any
  Filter: company_id from JWT
    - Forwarder: sees only quotes they submitted
    - Client: sees only quotes addressed to them

GET    /quotes/{id}
  Auth: Any (scoped by above rule)
  Returns: full detail with raw + mapped charge lines

PATCH  /quotes/{id}/status
  Auth: Client only
  Body: { status: "ACCEPTED" | "REJECTED", rejection_note?: str }
  Validation: can only accept/reject SUBMITTED quotes

PATCH  /quotes/charges/{id}/mapping
  Auth: Client only
  Body: { mapped_charge_id: int }
  Action:
    1. Update QuoteCharge.mapped_charge_id + mapped_charge_name
    2. Set mapping_tier = "HUMAN"
    3. Auto-save: POST /masters/charges/{mapped_charge_id}/aliases
       with the raw_charge_name as new alias
```

---

#### Phase 5 — Invoices API

##### Task 5.1 — `routers/invoices.py`

```
POST   /invoices/upload
  Auth: Forwarder
  Body: multipart/form-data { quote_id: int, file: PDF }
  Action:
    1. Verify quote exists + is ACCEPTED + belongs to this forwarder
    2. Save PDF to uploads/ directory
    3. Call extract_invoice_with_veryfi(file_path)
    4. Load buyer's Charge Master
    5. Run resolve_raw_charge_name() on extracted charge names
    6. Insert Invoice + InvoiceCharge rows
    7. Return preview: invoice_number + mapped charge lines

GET    /invoices?quote_id=X
  Auth: Client or Forwarder (scoped to their company)

GET    /invoices/{id}
  Auth: Client or Forwarder (scoped)
  Returns: invoice with raw + mapped charge lines

POST   /invoices/{id}/analyze
  Auth: Client only
  Action:
    1. Load invoice charges + corresponding quote charges
    2. Load existing invoice numbers for this client (duplicate check)
    3. Run detect_anomalies()
    4. Delete existing anomalies for this invoice (idempotent)
    5. Insert new anomaly rows
    6. Return AnomalyRead list

GET    /invoices/{id}/anomalies
  Auth: Client only
  Returns: stored anomaly results

PATCH  /invoices/charges/{id}/mapping
  Auth: Client only
  Body: { mapped_charge_id: int }
  Action: same as quote charge correction — update + auto-alias
```

---

#### Acceptance Criteria

- [ ] `POST /quotes` with 5 charge lines maps all of them and returns correct `mapping_tier` for each
- [ ] `"fuel surcharge"` with matching alias always maps to BAF via DICTIONARY tier
- [ ] Client accepting a quote returns `ACCEPTED` status; forwarder cannot accept
- [ ] `POST /invoices/upload` accepts a PDF and returns extracted charges
- [ ] `POST /invoices/{id}/analyze` returns at least one `UNEXPECTED_CHARGE` flag when invoice has a charge not in the quote
- [ ] Duplicate invoice number triggers `DUPLICATE_INVOICE` flag
- [ ] Manual mapping correction auto-saves a new alias (verify via `GET /masters/charges`)

---

#### Coordination Notes

- Import models from `app.models` and schemas from `app.schemas` (Tanishk owns these — don't modify them; raise a PR comment if you need a field added)
- Use `get_db` and `get_current_user` from `app.dependencies` (Tanishk's)
- If you need Tanishk to expose a helper (e.g., "get charge master for company X"), ask him to add it to `services/` rather than duplicating DB queries
- Yogesh will call your endpoints directly — keep response shapes stable once agreed



---

## Project Structure

```
freightauditpro/
├── README.md
├── README_tanishk.md
├── README_kaushik.md
├── README_yogesh.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py              ← Tanishk
│   │   ├── schemas.py             ← Tanishk
│   │   ├── routers/
│   │   │   ├── auth.py            ← Tanishk
│   │   │   ├── companies.py       ← Tanishk
│   │   │   ├── masters.py         ← Tanishk
│   │   │   ├── quotes.py          ← Kaushik
│   │   │   ├── invoices.py        ← Kaushik
│   │   │   ├── tracking.py        ← Tanishk
│   │   │   └── copilot.py         ← Yogesh
│   │   └── services/
│   │       ├── charge_mapping.py  ← Kaushik
│   │       ├── invoice_extraction.py ← Kaushik
│   │       ├── anomaly.py         ← Kaushik
│   │       ├── tracking.py        ← Tanishk
│   │       └── copilot.py         ← Yogesh
│   ├── alembic/                   ← Tanishk
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                 ← Yogesh (all pages)
│   │   └── components/            ← Yogesh (all components)
│   └── package.json
└── mock-data/
    └── generate_invoices.py       ← Manan
```

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase PostgreSQL database (free tier works)
- Veryfi API credentials (for invoice extraction)
- OpenAI API key (for Copilot)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in: DATABASE_URL, SECRET_KEY, VERYFI_CLIENT_ID, VERYFI_CLIENT_SECRET, OPENAI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000
npm run dev
```

### Generate Mock Invoice PDFs

```bash
cd mock-data
python generate_invoices.py
# Generates 15 freight invoice PDFs across 3 forwarder naming styles
# Intentional charge name variation to test mapping with aliases
```

---

## Environment Variables

```
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=your-jwt-secret
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
VERYFI_CLIENT_ID=your-veryfi-client-id
VERYFI_CLIENT_SECRET=your-veryfi-client-secret
VERYFI_USERNAME=your-veryfi-username
VERYFI_API_KEY=your-veryfi-api-key
OPENAI_API_KEY=sk-...
```

---

## Git Workflow

```
main
  └── dev                        ← all PRs target dev; main is production-only
        ├── feat/tanishk-foundation
        ├── feat/kaushik-intelligence
        └── feat/yogesh-frontend
```

- **Never commit directly to `main` or `dev`**
- Each person works on their named branch; open a PR into `dev` when a feature is complete
- Tanishk merges his foundation branch first (models + migrations) before Kaushik and Yogesh open PRs that depend on the schema
- Manan's mock-data work is fully standalone and can be merged at any point
