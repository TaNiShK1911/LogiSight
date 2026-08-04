"""
CockroachDB Cloud Managed MCP Server client for LogiSight Copilot.

Connects to the CockroachDB Cloud MCP Server at https://cockroachlabs.cloud/mcp
using the official Model Context Protocol (MCP) Python SDK with Streamable HTTP
transport.  Provides a LangChain-compatible tool for read-only ad hoc SQL queries
that the Copilot agent can invoke autonomously.

The MCP Server exposes tools like `execute_query` via the standard JSON-RPC 2.0
protocol (initialize → tools/list → tools/call).  Authentication uses a bearer
token from the CDB_MCP_TOKEN environment variable.

Environment variables:
    CDB_MCP_ENDPOINT  — MCP server URL (default: https://cockroachlabs.cloud/mcp)
    CDB_MCP_CLUSTER_ID — CockroachDB Cloud cluster ID
    CDB_MCP_TOKEN      — API key / bearer token for MCP authentication
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _get_mcp_config() -> dict[str, str]:
    """Return MCP Server configuration from environment."""
    return {
        "endpoint": os.environ.get(
            "CDB_MCP_ENDPOINT", "https://cockroachlabs.cloud/mcp"
        ),
        "cluster_id": os.environ.get("CDB_MCP_CLUSTER_ID", ""),
        "token": os.environ.get("CDB_MCP_TOKEN", ""),
    }


def is_mcp_configured() -> bool:
    """Check if MCP Server is configured with required credentials."""
    config = _get_mcp_config()
    return bool(config["cluster_id"] and config["token"])


async def _execute_mcp_query(query: str) -> str:
    """
    Execute a read-only SQL query against CockroachDB via the Managed MCP Server.

    Uses the official MCP Python SDK to:
      1. Connect via Streamable HTTP transport
      2. Call the `execute_query` tool with the given SQL

    Returns the query result as a string, or an error message.
    """
    config = _get_mcp_config()

    try:
        from mcp import Client
    except ImportError:
        return (
            "MCP SDK not installed. Run: pip install mcp"
        )

    headers = {
        "Authorization": f"Bearer {config['token']}",
    }

    try:
        async with Client(
            config["endpoint"],
            headers=headers,
        ) as client:
            # Discover available tools from the MCP server
            tools_response = await client.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            logger.info(f"MCP Server tools available: {tool_names}")

            # Find the query execution tool
            # CockroachDB MCP Server typically exposes 'execute_query'
            query_tool = None
            for candidate in ["execute_query", "run_query", "query"]:
                if candidate in tool_names:
                    query_tool = candidate
                    break

            if query_tool is None:
                logger.warning(
                    f"No query execution tool found on MCP server. "
                    f"Available tools: {tool_names}"
                )
                return f"MCP server has no query tool. Available: {tool_names}"

            # Call the query tool
            result = await client.call_tool(
                query_tool,
                arguments={
                    "sql": query,
                    "cluster_id": config["cluster_id"],
                },
            )

            # Extract text content from the MCP result
            if hasattr(result, "content") and result.content:
                parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                return "\n".join(parts) if parts else str(result)

            return str(result)

    except Exception as e:
        logger.error(f"MCP query failed: {e}")
        return f"MCP query error: {e}"


def create_mcp_tool():
    """
    Create a LangChain-compatible tool that queries CockroachDB via MCP Server.

    Returns a LangChain Tool or None if MCP is not configured.
    The tool wraps async MCP calls so the LangChain agent can invoke them.
    """
    if not is_mcp_configured():
        logger.info("CDB MCP Server not configured — skipping tool registration")
        return None

    from langchain_core.tools import Tool

    def run_mcp_query(query: str) -> str:
        """Execute a read-only SQL query via CockroachDB Cloud MCP Server."""
        try:
            # Bridge async MCP client into sync context for LangChain
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — use a new thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _execute_mcp_query(query))
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(_execute_mcp_query(query))
        except RuntimeError:
            # No event loop — create one
            return asyncio.run(_execute_mcp_query(query))

    return Tool(
        name="cockroachdb_mcp_query",
        description=(
            "Execute a read-only SQL query against the CockroachDB database "
            "via the CockroachDB Cloud Managed MCP Server. Use this for ad hoc "
            "queries about quotes, invoices, charges, anomalies, and tracking "
            "events. The query MUST be read-only SQL (SELECT only)."
        ),
        func=run_mcp_query,
    )
