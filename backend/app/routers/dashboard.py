"""
Dashboard stats endpoint (LogiSight).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_db
from app.models import Anomaly, Invoice, Quote

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    open_quotes: int
    anomalies_pending: int
    invoices_this_month: int
    total_accepted: int


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DashboardStatsResponse:
    """
    Return dashboard statistics scoped to the current user's company.
    """
    role = current_user.get("role")
    cid = current_user.get("company_id")

    # Build base quote filter
    base_filter = []
    if role == "client" and cid is not None:
        base_filter.append(Quote.buyer_id == cid)
    elif role == "forwarder" and cid is not None:
        base_filter.append(Quote.forwarder_id == cid)
    elif role != "super_admin":
        raise HTTPException(status_code=403, detail="Invalid scope")

    # Open quotes (status = SUBMITTED)
    open_q = select(func.count(Quote.id)).where(
        Quote.status == "SUBMITTED", *base_filter
    )
    open_result = await db.execute(open_q)
    open_quotes = open_result.scalar() or 0

    # Total accepted
    accepted_q = select(func.count(Quote.id)).where(
        Quote.status == "ACCEPTED", *base_filter
    )
    accepted_result = await db.execute(accepted_q)
    total_accepted = accepted_result.scalar() or 0

    # Invoices this month
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    inv_q = (
        select(func.count(Invoice.id))
        .join(Quote, Quote.id == Invoice.quote_id)
        .where(Invoice.uploaded_at >= first_of_month, *base_filter)
    )
    inv_result = await db.execute(inv_q)
    invoices_this_month = inv_result.scalar() or 0

    # Anomalies pending (total anomaly count for user's invoices)
    anom_q = (
        select(func.count(Anomaly.id))
        .join(Invoice, Invoice.id == Anomaly.invoice_id)
        .join(Quote, Quote.id == Invoice.quote_id)
        .where(*base_filter)
    )
    anom_result = await db.execute(anom_q)
    anomalies_pending = anom_result.scalar() or 0

    return DashboardStatsResponse(
        open_quotes=open_quotes,
        anomalies_pending=anomalies_pending,
        invoices_this_month=invoices_this_month,
        total_accepted=total_accepted,
    )
