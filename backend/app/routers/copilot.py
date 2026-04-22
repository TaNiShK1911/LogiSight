"""
LogiSight Copilot — Natural language queries over freight data.
Phase 4: AI & Advanced Services
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, CurrentUser
from app.schemas import CopilotQueryRequest, CopilotQueryResponse
from app.services.copilot import run_copilot_query

router = APIRouter()


@router.post("/query", response_model=CopilotQueryResponse)
async def copilot_query(
    body: CopilotQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CopilotQueryResponse:
    """
    Execute a natural language query against the freight database.
    
    Only available to Client users. Forwarders cannot access the Copilot.
    All queries are strictly scoped to the user's company_id.
    """
    # Only Client users can access the Copilot
    if current_user.get("role") != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Client users can access the Copilot",
        )
    
    # Ensure company_id is present
    company_id = current_user.get("company_id")
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company scope required for Copilot access",
        )
    
    # Run the query
    answer = await run_copilot_query(body.question, company_id)
    
    return CopilotQueryResponse(answer=answer)
