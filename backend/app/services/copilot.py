"""
LogiSight Copilot — LangChain SQL Agent with strict company_id filtering.
Phase 4: AI & Advanced Services
"""

from __future__ import annotations

import os
from typing import Any

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI


# Forbidden keywords for write operations
FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "truncate",
    "alter", "create", "grant", "revoke", "replace"
]


def _get_database_url() -> str:
    """Get sync PostgreSQL URL for LangChain SQLDatabase."""
    # Try SUPABASE_DB_URL first (connection pooler on port 6543)
    url = os.environ.get("SUPABASE_DB_URL", "")

    # Fallback to DATABASE_URL if SUPABASE_DB_URL not set
    if not url:
        url = os.environ.get("DATABASE_URL", "")

    if not url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL is not set")

    # LangChain SQLDatabase requires sync driver (psycopg2)
    # Convert asyncpg URL to psycopg2 URL
    if "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://")

    return url


def _get_openai_api_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return key


def is_write_attempt(question: str) -> bool:
    """Check if the question contains forbidden write operation keywords."""
    q = question.lower()
    return any(kw in q for kw in FORBIDDEN_KEYWORDS)


def get_copilot_agent(company_id: int) -> Any:
    """
    Create a LangChain SQL Agent for the Copilot with strict company_id filtering.

    Args:
        company_id: The client company ID to scope all queries

    Returns:
        LangChain SQL Agent configured for freight audit queries
    """
    db_url = _get_database_url()
    api_key = _get_openai_api_key()

    # Create SQLDatabase connection with specific tables
    db = SQLDatabase.from_uri(
        db_url,
        include_tables=[
            "companies", "countries", "currencies", "airports",
            "quotes", "quote_charges", "invoices", "invoice_charges",
            "anomalies", "charges", "charge_aliases", "tracking_events",
        ],
        sample_rows_in_table_info=2,
    )

    # Create ChatOpenAI LLM with token limits
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
        max_tokens=800,  # Limit response length to control costs
    )

    # Enhanced system prompt with Chain of Thought reasoning
    prefix = f"""You are LogiSight Copilot — an expert freight data analyst.
You help users query their freight database using natural language.

THINKING PROCESS — always follow these steps before writing SQL:
1. Understand what the user is asking (identify the main metric, time range, filters)
2. Identify which tables are needed
3. Identify how to JOIN them correctly
4. Write the SQL step by step
5. Double check: is it SELECT only? is it scoped to company_id = {company_id}? is it limited to 100 rows?

CRITICAL SECURITY RULE - YOU MUST ALWAYS FOLLOW THIS:
- ALWAYS filter ALL queries to show only data for company_id = {company_id} (this is the user's company)
- NEVER return data from other companies
- The user is a CLIENT (buyer), so use these filters:
  * For quotes table: WHERE q.buyer_id = {company_id}
  * For charges table: WHERE c.company_id = {company_id}
  * For invoices: join through quotes and use WHERE q.buyer_id = {company_id}
  * For anomalies: join through invoices → quotes and use WHERE q.buyer_id = {company_id}
- DO NOT filter by forwarder company_id - that's the carrier, not the user
- The user wants to see THEIR quotes/invoices, not filter by forwarder

STRICT RULES:
1. ONLY run SELECT queries. NEVER run INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE.
2. If the user asks to modify or delete data — refuse with: "I can only read data, not modify it."
3. Always LIMIT to 100 rows unless user asks for more (max 500).
4. Always use table aliases for readability.
5. Filter is_active = true for companies unless asked otherwise.

KEY SCHEMA CONTEXT:
- companies.type = 'client' means buyer, 'forwarder' means carrier
- quotes.forwarder_id → companies (forwarder), quotes.buyer_id → companies (client)
- quote_charges  = what forwarder QUOTED (promised amounts)
- invoice_charges = what forwarder actually BILLED
- variance = invoice_charges.amount - quote_charges.amount
- anomalies.variance > 0 means overcharged, < 0 means undercharged
- anomalies.flag_type: AMOUNT_MISMATCH, UNEXPECTED_CHARGE, MISSING_CHARGE, DUPLICATE_INVOICE
- mapping_tier: DICTIONARY, HUMAN, UNMAPPED
- basis values: 'Per KG', 'Per Shipment', 'Per CBM', 'Flat Rate'
- quote status: SUBMITTED, ACCEPTED, REJECTED

QUOTE vs INVOICE COMPARISON PATTERN:
SELECT
    q.tracking_number,
    co_fwd.name        AS forwarder,
    qc.mapped_charge_name AS charge,
    qc.amount          AS quoted_amount,
    ic.amount          AS invoiced_amount,
    (ic.amount - qc.amount) AS variance
FROM quotes q
JOIN companies co_fwd ON co_fwd.id = q.forwarder_id
JOIN quote_charges qc ON qc.quote_id = q.id
JOIN invoices inv     ON inv.quote_id = q.id
JOIN invoice_charges ic
    ON ic.invoice_id = inv.id
    AND ic.mapped_charge_id = qc.mapped_charge_id
WHERE q.buyer_id = {company_id}
  AND q.status = 'ACCEPTED'
LIMIT 100;

RESPONSE GUIDELINES:
- Provide clear, narrative summaries in paragraph form
- Avoid using markdown tables - present data in flowing text instead
- Format currency amounts consistently (e.g., $1,234.56)
- Use markdown formatting sparingly:
  * **Bold** for emphasis on key metrics only
  * Bullet points only when listing 3+ distinct items
  * Keep responses conversational and easy to read
- For numerical comparisons, describe them in sentences rather than tables
- Always include units (currency, weight, volume) with numbers
- For anomalies, explain what the flag means in plain language
- If no data found, say so clearly and suggest what data might be available
- Keep responses concise and well-organized in paragraph form
- Always scope to company_id = {company_id}

EXAMPLE RESPONSE FORMAT:
For "Which forwarder had the most anomalies?":

Based on your freight data, DSV Local had the most anomalies this month with 10 discrepancies. The primary issue was amount mismatches, where the invoiced amounts differed from the quoted amounts. This represents a significant variance that may require review with the forwarder.

FALLBACK RESPONSES:
- If query fails: "I couldn't execute that query. Please try rephrasing your question or ask about quotes, invoices, or anomalies."
- If no results: "I didn't find any data matching your query. You can ask about your quotes, invoices, charges, or tracking events."
- If ambiguous: "Could you clarify what you're looking for? For example, are you asking about quotes, invoices, or anomalies?"

Remember: NEVER access data from other companies. All queries must filter by company_id = {company_id} or quotes.buyer_id = {company_id}.
"""

    # Create SQL Agent with OpenAI tools
    agent = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="openai-tools",
        prefix=prefix,
        verbose=True,  # Enable verbose for debugging
        max_iterations=10,  # Limit iterations to prevent runaway
        max_execution_time=60,  # 60 second timeout
        handle_parsing_errors=True,  # Gracefully handle parsing errors
    )

    return agent


async def run_copilot_query(question: str, company_id: int) -> str:
    """
    Execute a natural language query against the freight database.

    Args:
        question: Natural language question from the user
        company_id: Client company ID for data scoping

    Returns:
        Plain English answer from the SQL Agent

    Raises:
        ValueError: If question is empty or contains forbidden keywords
        RuntimeError: If OpenAI API key or database URL is not configured
    """
    import asyncio

    # Validate input
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    # Check for write attempts
    if is_write_attempt(question):
        return "I can only read data, not modify it. Please ask a question about your quotes, invoices, charges, or tracking data."

    try:
        agent = get_copilot_agent(company_id)

        # Run the synchronous invoke in a thread pool to avoid blocking
        result = await asyncio.to_thread(agent.invoke, {"input": question})

        # Extract the output from the agent result
        if isinstance(result, dict):
            answer = result.get("output", "")
        else:
            answer = str(result)

        # Fallback if no answer
        if not answer or not answer.strip():
            return "I couldn't find an answer to that question. Please try rephrasing or ask about your quotes, invoices, charges, or anomalies."

        return answer.strip()

    except RuntimeError as e:
        # Configuration errors
        error_msg = str(e)
        if "OPENAI_API_KEY" in error_msg:
            return "The Copilot service is not configured. Please contact your administrator to set up the OpenAI API key."
        elif "DATABASE_URL" in error_msg:
            return "Database connection error. Please contact your administrator."
        raise

    except Exception as e:
        # General errors - provide helpful fallback
        error_msg = str(e).lower()

        if "readonly" in error_msg or "permission denied" in error_msg:
            return "This query is not allowed. I can only read data, not modify it."
        elif "timeout" in error_msg:
            return "The query took too long to execute. Please try a simpler question or narrow down your search criteria."
        elif "syntax error" in error_msg or "invalid" in error_msg:
            return "I had trouble understanding your question. Could you rephrase it? For example, ask about 'quotes from last month' or 'invoices with anomalies'."
        else:
            return "I encountered an error processing your question. Please try rephrasing or ask about your quotes, invoices, charges, or tracking events."

