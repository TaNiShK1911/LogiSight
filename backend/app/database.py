"""
Async SQLAlchemy engine and session factory for LogiSight.
Supports CockroachDB Cloud (via asyncpg) and local PostgreSQL.
Reads COCKROACHDB_URL first, falls back to DATABASE_URL.
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
    """
    Resolve the database connection URL.
    Priority: COCKROACHDB_URL → DATABASE_URL.
    CockroachDB Cloud URLs are automatically converted to asyncpg format.
    """
    url = os.environ.get("COCKROACHDB_URL", "")

    if not url:
        url = os.environ.get("DATABASE_URL", "")

    if not url:
        raise RuntimeError(
            "Neither COCKROACHDB_URL nor DATABASE_URL is set. "
            "Set one of these environment variables to connect to the database."
        )

    # Convert cockroachdb:// to postgresql+asyncpg:// for async driver
    if url.startswith("cockroachdb://"):
        url = url.replace("cockroachdb://", "cockroachdb+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "cockroachdb+asyncpg://", 1)

    # asyncpg doesn't support sslmode in the URL query string
    if "sslmode=verify-full" in url:
        url = url.replace("?sslmode=verify-full", "")
        url = url.replace("&sslmode=verify-full", "")

    return url


engine = create_async_engine(
    _database_url(),
    echo=os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"ssl": "require"} if "cockroachlabs.cloud" in os.environ.get("COCKROACHDB_URL", "") else {}
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session (for FastAPI dependencies)."""
    async with async_session_factory() as session:
        yield session
