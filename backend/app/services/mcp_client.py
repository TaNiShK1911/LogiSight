"""
CockroachDB Cloud MCP Server client for LogiSight Copilot.
Provides read-only ad hoc query capability during Copilot conversations.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _get_mcp_config() -> dict[str, str]:
    """Return MCP Server configuration from environment."""
    return {
        "endpoint": os.environ.get("CDB_MCP_ENDPOINT", "https://cockroachlabs.cloud/mcp"),
        "cluster_id": os.environ.get("CDB_MCP_CLUSTER_ID", ""),
        "token": os.environ.get("CDB_MCP_TOKEN", ""),
    }


def is_mcp_configured() -> bool:
    """Check if MCP Server is configured."""
    config = _get_mcp_config()
    return bool(config["cluster_id"] and config["token"])


def create_mcp_tool():
    """
    Create a LangChain-compatible tool that queries CockroachDB via MCP Server.

    Returns a LangChain Tool or None if MCP is not configured.
    """
    if not is_mcp_configured():
        logger.info("CDB MCP Server not configured — skipping tool registration")
        return None

    config = _get_mcp_config()

    from langchain_core.tools import Tool

    def run_mcp_query(query: str) -> str:
        """Execute a read-only SQL query via CockroachDB MCP Server."""
        import httpx

        try:
            response = httpx.post(
                f"{config['endpoint']}/v1/query",
                headers={
                    "Authorization": f"Bearer {config['token']}",
                    "Content-Type": "application/json",
                },
                json={
                    "cluster_id": config["cluster_id"],
                    "query": query,
                    "read_only": True,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("result", data))
        except Exception as e:
            logger.error(f"MCP query failed: {e}")
            return f"MCP query error: {e}"

    return Tool(
        name="cockroachdb_query",
        description=(
            "Execute a read-only SQL query against the CockroachDB database "
            "to retrieve freight audit data. Use this for ad hoc queries about "
            "quotes, invoices, charges, anomalies, and tracking events."
        ),
        func=run_mcp_query,
    )
