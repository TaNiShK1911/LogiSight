"""
LogiSight Copilot — LangChain SQL Agent with strict company_id filtering.
Uses Groq (LLaMA 3.3) as the primary LLM, with Bedrock (Claude) as fallback.
Memory events stored in CockroachDB.  Optionally queries via CockroachDB
Cloud Managed MCP Server when configured.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

from app.services.bedrock_client import get_chat_model
from app.services.mcp_client import create_mcp_tool, is_mcp_configured

logger = logging.getLogger(__name__)

# Forbidden keywords for write operations
FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "truncate",
    "alter", "create", "grant", "revoke", "replace",
]


def _get_database_url() -> str:
    """Get sync PostgreSQL URL for LangChain SQLDatabase (psycopg2)."""
    url = os.environ.get("COCKROACHDB_URL", "")
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("COCKROACHDB_URL or DATABASE_URL is not set")

    # LangChain SQLDatabase requires sync driver (psycopg2)
    if "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif url.startswith("cockroachdb://"):
        url = url.replace("cockroachdb://", "postgresql://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://")

    # Fix psycopg2 SSL verification on Windows for CockroachDB Serverless
    if "sslmode=verify-full" in url:
        url = url.replace("sslmode=verify-full", "sslmode=require")

    return url


def is_write_attempt(question: str) -> bool:
    """Check if the question contains forbidden write operation keywords."""
    q = question.lower()
    return any(kw in q for kw in FORBIDDEN_KEYWORDS)


# Cache the database to avoid slow reflection on every request
_db_cache = None
_table_info_cache = None


def get_database_and_llm():
    """Return cached SQLDatabase and a fresh Bedrock LLM instance."""
    global _db_cache

    db_url = _get_database_url()

    if _db_cache is None:
        from sqlalchemy import create_engine
        import types

        engine = create_engine(db_url)

        # The PGDialect._get_server_version_info() parses pg_catalog.version()
        # output expecting "PostgreSQL X.Y.Z" but CockroachDB v26+ returns
        # "CockroachDB CCL v26.2.1 ..." which doesn't match, raising
        # AssertionError. We monkey-patch the method on the dialect instance
        # to return a compatible version tuple.
        def _patched_get_server_version_info(self, connection):
            return (13, 0, 0)

        engine.dialect._get_server_version_info = types.MethodType(
            _patched_get_server_version_info, engine.dialect
        )

        _db_cache = SQLDatabase(
            engine=engine,
            include_tables=[
                "companies", "countries", "currencies", "airports",
                "quotes", "quote_charges", "invoices", "invoice_charges",
                "anomalies", "charges", "charge_aliases", "tracking_events",
            ],
            sample_rows_in_table_info=2,
        )

    llm = get_chat_model(temperature=0.0)
    return _db_cache, llm


def get_table_info_cached(db):
    global _table_info_cache
    if _table_info_cache is None:
        logger.info("Fetching table info for the first time...")
        _table_info_cache = db.get_table_info()
    return _table_info_cache


async def _record_memory_event(
    session_id: str | None,
    tenant_id: int,
    event_type: str,
    content: dict,
) -> None:
    """Write a memory event row to CockroachDB (fire-and-forget)."""
    try:
        from app.database import async_session_factory
        from app.models.copilot_memory import CopilotMemoryEvent, CopilotSession
        from sqlalchemy import select

        async with async_session_factory() as session:
            actual_session_id = uuid.UUID(session_id) if session_id else uuid.uuid4()
            
            # Ensure the session exists
            result = await session.execute(
                select(CopilotSession).where(CopilotSession.id == actual_session_id)
            )
            if not result.scalar_one_or_none():
                new_sess = CopilotSession(
                    id=actual_session_id,
                    tenant_id=tenant_id,
                    user_id="copilot_user", # placeholder since we don't have user_id here easily
                )
                session.add(new_sess)
                await session.flush()

            event = CopilotMemoryEvent(
                id=uuid.uuid4(),
                session_id=actual_session_id,
                tenant_id=tenant_id,
                event_type=event_type,
                content=content,
            )
            session.add(event)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to record copilot memory event: {e}")


async def _generate_sql(
    db,
    llm,
    question: str,
    company_id: int,
    error_context: str = "",
) -> str:
    """
    Generate a single PostgreSQL/CockroachDB-compatible SQL query for the
    given natural-language question, scoped to company_id.

    Shared by both the MCP path (which needs real SQL to hand to the
    CockroachDB Cloud Managed MCP Server's execute_query tool — an English
    question is not valid SQL) and the direct-SQL fallback path.
    """
    sql_template = f"""You are a PostgreSQL expert for a freight platform.
Given an input question, create a syntactically correct PostgreSQL query to run.
Unless the user specifies a specific number of examples, limit your query to at most 100 results using the LIMIT clause.
Never query for all columns from a specific table; only ask for the relevant columns given the question.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

CRITICAL SECURITY RULE:
- ALWAYS filter ALL queries to show only data for company_id = {company_id}
- The user is a CLIENT (buyer), so use these filters:
  * For quotes table: WHERE buyer_id = {company_id}
  * For charges table: WHERE company_id = {company_id}
  * For invoices: join through quotes and use WHERE quotes.buyer_id = {company_id}
  * For anomalies: join through invoices -> quotes and use WHERE quotes.buyer_id = {company_id}

SCHEMA HINTS (CRITICAL):
- The `invoices` table DOES NOT have an `amount` column. You MUST join `invoice_charges` (on invoices.id = invoice_charges.invoice_id) and SUM(invoice_charges.amount) to get invoice totals.
- The `quotes` table DOES NOT have an `amount` column. You MUST join `quote_charges` (on quotes.id = quote_charges.quote_id) and SUM(quote_charges.amount) to get quote totals.
- When asked about "charge types" or "specific charges", join `invoice_charges` to use `mapped_charge_name`. Do NOT use `anomalies.flag_type` (which is an anomaly category like AMOUNT_MISMATCH, not a charge).
- SQL TRAP WARNING: NEVER join `quote_charges` and `invoice_charges` in the same main query block! This causes a Cartesian product and multiplies the sums. Use separate subqueries for quote totals and invoice totals.
- SQL TRAP WARNING: Do NOT use INNER JOIN between quotes and invoices if you want the total of ALL quotes. (That would filter out quotes without invoices).
- NEVER apply a LIMIT clause when performing aggregate calculations (SUM, COUNT, etc.).

OUTPUT RULE:
- RETURN ONLY THE SQL QUERY.
- DO NOT INCLUDE ANY MARKDOWN BACKTICKS OR EXPLANATIONS.
- If you explain, the system will break.

Only use the following tables:
{{table_info}}
{{error_context}}
Question: {{question}}
SQLQuery:"""

    sql_prompt = PromptTemplate.from_template(sql_template)
    sql_chain = (
        RunnablePassthrough.assign(table_info=lambda _: get_table_info_cached(db))
        | sql_prompt
        | llm.bind(stop=["\nSQLResult:"])
        | StrOutputParser()
    )

    sql_query = await asyncio.to_thread(
        sql_chain.invoke,
        {"question": question, "error_context": error_context},
    )
    return sql_query.replace("```sql", "").replace("```", "").strip()


async def _generate_answer(llm, question: str, query: str, result: str) -> str:
    """Turn a SQL query + its result into a natural-language answer."""
    answer_template = """Based on the SQL query result, answer the user's question in a clear, narrative summary.
Avoid using markdown tables. Keep it conversational.
IMPORTANT: Format any ALL_CAPS database enum values or internal codes (e.g., AMOUNT_MISMATCH, UNMAPPED) into clean, human-readable Title Case (e.g., "Amount Mismatch", "Unmapped"). Never expose raw column names or snake_case constants to the user.
If no data was found or there was an error, say so clearly.

Question: {question}
SQL Query: {query}
SQL Result: {result}
Answer:"""
    answer_prompt = PromptTemplate.from_template(answer_template)
    answer_chain = answer_prompt | llm | StrOutputParser()

    final_answer = await asyncio.to_thread(
        answer_chain.invoke,
        {"question": question, "query": query, "result": result},
    )
    return final_answer.strip()


async def run_copilot_query(
    question: str,
    company_id: int,
    session_id: str | None = None,
) -> str:
    """
    Execute a natural language query against the freight database.
    Uses AWS Bedrock (Claude) as the LLM.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if is_write_attempt(question):
        return "I can only read data, not modify it. Please ask a question about your quotes, invoices, charges, or tracking data."

    # Record the user query as a memory event
    await _record_memory_event(
        session_id=session_id,
        tenant_id=company_id,
        event_type="user_message",
        content={"question": question},
    )

    try:
        # DB + LLM are needed for SQL generation on both the MCP path and
        # the direct-SQL fallback path, so resolve them up front.
        db, llm = await asyncio.to_thread(get_database_and_llm)

        # ── MCP path: if configured, generate real SQL first, then execute
        # it via the CockroachDB Cloud Managed MCP Server. The MCP server's
        # execute_query tool expects SQL, not an English question, so we
        # must run the same NL→SQL generation step used by the fallback
        # path before calling it. ──
        if is_mcp_configured():
            try:
                mcp_tool = create_mcp_tool()
                if mcp_tool is not None:
                    mcp_sql = await _generate_sql(db, llm, question, company_id)
                    logger.info(
                        f"Routing Copilot query through MCP Server. SQL: {mcp_sql}"
                    )
                    mcp_result = await asyncio.to_thread(mcp_tool.run, mcp_sql)
                    if mcp_result and "error" not in mcp_result.lower():
                        answer = await _generate_answer(
                            llm, question, mcp_sql, mcp_result
                        )
                        await _record_memory_event(
                            session_id=session_id,
                            tenant_id=company_id,
                            event_type="agent_message",
                            content={
                                "question": question,
                                "source": "mcp",
                                "sql_query": mcp_sql,
                                "answer": answer,
                            },
                        )
                        return answer
                    else:
                        logger.warning(
                            f"MCP returned error, falling back to direct SQL: {mcp_result}"
                        )
            except Exception as e:
                logger.warning(f"MCP query failed, falling back to direct SQL: {e}")

        # ── Direct SQL path: existing SQLDatabase chain with retry loop ──
        max_retries = 3
        sql_query = ""
        sql_result = ""
        error_context = ""

        for attempt in range(max_retries):
            sql_query = await _generate_sql(
                db, llm, question, company_id, error_context
            )
            logger.info(f"Generated SQL (Attempt {attempt + 1}): {sql_query}")

            try:
                sql_result = await asyncio.to_thread(db.run, sql_query)
                logger.info(f"SQL Result: {sql_result}")
                break  # Success!
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"SQL Execution Error (Attempt {attempt + 1}): {e}")
                    sql_result = (
                        f"Error executing query after {max_retries} attempts: {e}"
                    )
                else:
                    logger.warning(
                        f"SQL retry triggered on Attempt {attempt + 1} due to error."
                    )
                    error_context = (
                        f"\nPREVIOUS ERROR: The query you generated failed "
                        f"with the following error:\n{e}\nPlease fix the syntax "
                        f"or column names in your new query.\n"
                    )

        answer = await _generate_answer(llm, question, sql_query, sql_result)

        # Record the agent response as a memory event
        await _record_memory_event(
            session_id=session_id,
            tenant_id=company_id,
            event_type="agent_message",
            content={
                "question": question,
                "sql_query": sql_query,
                "answer": answer,
            },
        )

        return answer

    except RuntimeError as e:
        error_msg = str(e)
        if "DATABASE_URL" in error_msg or "COCKROACHDB_URL" in error_msg:
            return "Database connection error. Please contact your administrator."
        raise

    except Exception as e:
        logger.error(f"Copilot Error: {e}")
        return "I encountered an error processing your question. Please try rephrasing or ask about your quotes, invoices, charges, or tracking events."