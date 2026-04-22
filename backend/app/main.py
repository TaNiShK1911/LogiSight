"""
LogiSight FastAPI application entrypoint.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import auth, companies, copilot, invoices, masters, quotes, tracking, users, debug


def _cors_allow_origins() -> list[str]:
    """Comma-separated `CORS_ORIGINS` env, or local Vite defaults."""
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Dispose the async engine cleanly on shutdown."""
    yield
    await engine.dispose()


app = FastAPI(
    title="LogiSight API",
    description="Multi-tenant freight audit platform backend",
    version="0.1.0",
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
app.include_router(debug.router, prefix="/debug", tags=["debug"])


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe for deployment and local checks."""
    return {"status": "ok", "service": "LogiSight"}
