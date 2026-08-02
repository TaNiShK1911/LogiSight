"""
LogiSight Copilot — LangChain SQL Agent with strict company_id filtering.
Uses AWS Bedrock (Claude) for LLM. Memory events stored in CockroachDB.
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
        db, llm = await asyncio.to_thread(get_database_and_llm)

        # 1. Generate and Execute SQL with Retry Loop
        max_retries = 3
        sql_query = ""
        sql_result = ""
        error_context = ""

        for attempt in range(max_retries):
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
- The `invoices` table DOES NOT have an `amount` column. You MUST join `invoice_charges` to get invoice amounts.
- The `quotes` table DOES NOT have an `amount` column. You MUST join `quote_charges` to get quote amounts.

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
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
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

        # 2. Generate Answer
        answer_template = """Based on the SQL query result, answer the user's question in a clear, narrative summary.
Avoid using markdown tables. Keep it conversational.
If no data was found or there was an error, say so clearly.

Question: {question}
SQL Query: {query}
SQL Result: {result}
Answer:"""
        answer_prompt = PromptTemplate.from_template(answer_template)
        answer_chain = answer_prompt | llm | StrOutputParser()

        final_answer = await asyncio.to_thread(
            answer_chain.invoke,
            {"question": question, "query": sql_query, "result": sql_result},
        )

        answer = final_answer.strip()

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
