"""
LogiSight FastAPI application entrypoint.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import auth, companies, copilot, dashboard, invoices, masters, quotes, tracking, users, debug


def _cors_allow_origins() -> list[str]:
    """Comma-separated `CORS_ORIGINS` env, or local Vite defaults."""
    # Check for explicit allowed origin (production Vercel domain)
    allowed = os.environ.get("CORS_ALLOWED_ORIGIN", "").strip()
    if allowed:
        origins = [allowed]
    else:
        origins = []

    # Also check CORS_ORIGINS for a comma-separated list
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw == "*":
        return ["*"]
    if raw:
        origins.extend([part.strip() for part in raw.split(",") if part.strip()])

    # Default local dev origins
    if not origins:
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "https://logisight.vercel.app",
        ]
    else:
        # Always include local dev origins alongside production
        for local in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "https://logisight.vercel.app"):
            if local not in origins:
                origins.append(local)

    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Dispose the async engine cleanly on shutdown."""
    yield
    await engine.dispose()


app = FastAPI(
    title="LogiSight API",
    description="Multi-tenant freight audit platform backend",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(masters.router, prefix="/masters", tags=["masters"])
app.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
app.include_router(copilot.router, prefix="/copilot", tags=["copilot"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe for deployment and local checks."""
    return {"status": "ok", "service": "LogiSight"}
