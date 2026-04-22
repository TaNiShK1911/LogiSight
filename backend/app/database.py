"""
Async SQLAlchemy engine and session factory for LogiSight.
Uses Supabase PostgreSQL via asyncpg; expects DATABASE_URL (postgresql+asyncpg://...).
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Load environment variables from .env file
load_dotenv()


class Base(DeclarativeBase):
    """Declarative base for all LogiSight ORM models."""

    pass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


engine = create_async_engine(
    _database_url(),
    echo=os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session (for FastAPI dependencies in later phases)."""
    async with async_session_factory() as session:
        yield session
