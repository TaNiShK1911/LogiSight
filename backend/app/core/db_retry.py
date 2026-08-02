"""
CockroachDB serialization failure retry logic.

CockroachDB uses serializable transactions by default. Under contention,
transactions may fail with SQLSTATE 40001 (serialization_failure) and must be retried.
This module provides a decorator for automatic retry with exponential backoff.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, TypeVar

from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# CockroachDB serialization failure SQLSTATE
_SERIALIZATION_FAILURE = "40001"

_MAX_RETRIES = 3
_BASE_DELAY_S = 0.1  # 100ms


def _is_serialization_failure(exc: OperationalError) -> bool:
    """Check if the OperationalError is a CockroachDB serialization failure."""
    orig = getattr(exc, "orig", None)
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
        if pgcode == _SERIALIZATION_FAILURE:
            return True
    # Fallback: check the string representation
    return _SERIALIZATION_FAILURE in str(exc)


def retry_on_serialization_failure(
    max_retries: int = _MAX_RETRIES,
    base_delay: float = _BASE_DELAY_S,
) -> Callable:
    """
    Decorator that retries an async function on CockroachDB serialization failures.

    Usage:
        @retry_on_serialization_failure()
        async def my_write_operation(session, ...):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as exc:
                    if not _is_serialization_failure(exc):
                        raise  # Not a serialization failure — don't retry

                    last_exc = exc

                    if attempt == max_retries:
                        logger.error(
                            f"[CDB RETRY] {func.__name__}: serialization failure after "
                            f"{max_retries + 1} attempts, giving up"
                        )
                        raise

                    # Exponential backoff with jitter
                    delay = base_delay * (2**attempt) + random.uniform(0, base_delay)
                    logger.warning(
                        f"[CDB RETRY] {func.__name__}: serialization failure on attempt "
                        f"{attempt + 1}/{max_retries + 1}, retrying in {delay:.3f}s"
                    )
                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_exc:
                raise last_exc
            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator
