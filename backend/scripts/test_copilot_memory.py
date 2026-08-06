import asyncio
import os
import uuid
import logging
import sys

# Add backend dir to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.copilot import run_copilot_query
from app.database import async_session_factory
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Assume company_id = 1 for testing
    company_id = 1
    
    # Layer 1 test: Same-session context
    print("--- Testing Layer 1: Same-Session Context ---")
    session_1 = str(uuid.uuid4())
    print(f"Session 1: {session_1}")
    
    q1 = "What invoices do we have from Acme?"
    print(f"\nUser (S1, Turn 1): {q1}")
    a1 = await run_copilot_query(q1, company_id, session_id=session_1)
    print(f"Agent: {a1}")
    
    q2 = "What about last month specifically?"
    print(f"\nUser (S1, Turn 2): {q2}")
    a2 = await run_copilot_query(q2, company_id, session_id=session_1)
    print(f"Agent: {a2}")
    
    # Layer 2 test: Cross-session context
    print("\n--- Testing Layer 2: Cross-Session Context ---")
    session_2 = str(uuid.uuid4())
    print(f"Session 2: {session_2}")
    
    # We ask a question that requires recalling "Acme" from session 1, maybe something vague
    q3 = "Can you show me the total amount for that company we just discussed in my other session?"
    print(f"\nUser (S2, Turn 1): {q3}")
    a3 = await run_copilot_query(q3, company_id, session_id=session_2)
    print(f"Agent: {a3}")

if __name__ == "__main__":
    asyncio.run(main())
