"""
Alembic environment for async SQLAlchemy + CockroachDB / PostgreSQL (LogiSight).
Reads COCKROACHDB_URL or DATABASE_URL from environment.
"""

import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

load_dotenv()

from app.database import Base  # noqa: E402
from app import models  # noqa: F401, E402  — triggers model registration
from app.models.copilot_memory import (  # noqa: F401, E402
    CopilotSession,
    CopilotMemoryEvent,
    ChargeEmbedding,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_db_url() -> str:
    """Resolve database URL: COCKROACHDB_URL → DATABASE_URL."""
    url = os.environ.get("COCKROACHDB_URL", "")
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "Neither COCKROACHDB_URL nor DATABASE_URL is set for Alembic migrations"
        )
    # Ensure asyncpg format
    if url.startswith("cockroachdb://"):
        url = url.replace("cockroachdb://", "cockroachdb+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "cockroachdb+asyncpg://", 1)

    if "sslmode=verify-full" in url:
        url = url.replace("?sslmode=verify-full", "")
        url = url.replace("&sslmode=verify-full", "")
    return url


db_url = _resolve_db_url()


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        db_url, 
        poolclass=pool.NullPool,
        connect_args={"ssl": "require"} if "cockroachlabs.cloud" in os.environ.get("COCKROACHDB_URL", "") else {}
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
