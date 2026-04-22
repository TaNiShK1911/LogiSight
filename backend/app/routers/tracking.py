"""Shipment tracking lists and event history (LogiSight)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, get_current_user, get_db
from app.models import Quote, TrackingEvent
from app.schemas import TrackingEventRead, TrackingShipmentRead
from app.services.serialization import build_tracking_shipment, tracking_event_to_read

router = APIRouter()


@router.get("", response_model=list[TrackingShipmentRead])
async def list_tracking(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[TrackingShipmentRead]:
    role = current_user.get("role")
    cid = current_user.get("company_id")

    stmt = (
        select(Quote)
        .options(
            selectinload(Quote.tracking_events),
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
            selectinload(Quote.origin_airport),
            selectinload(Quote.destination_airport),
        )
        .order_by(Quote.created_at.desc())
    )
    if role == "client" and cid is not None:
        stmt = stmt.where(Quote.buyer_id == cid)
    elif role == "forwarder" and cid is not None:
        stmt = stmt.where(Quote.forwarder_id == cid)
    elif role == "super_admin":
        pass
    else:
        raise HTTPException(status_code=403, detail="Invalid scope")

    r = await db.execute(stmt)
    quotes = list(r.scalars().all())
    return [build_tracking_shipment(q, list(q.tracking_events or [])) for q in quotes]


@router.get("/{quote_id}/events", response_model=list[TrackingEventRead])
async def list_tracking_events(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[TrackingEventRead]:
    q = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
        )
    )
    quote = q.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    role = current_user.get("role")
    cid = current_user.get("company_id")
    if role == "super_admin":
        pass
    elif role == "client" and cid is not None and int(quote.buyer_id) == int(cid):
        pass
    elif role == "forwarder" and cid is not None and int(quote.forwarder_id) == int(cid):
        pass
    else:
        raise HTTPException(status_code=404, detail="Shipment not found")

    er = await db.execute(
        select(TrackingEvent)
        .where(TrackingEvent.quote_id == quote_id)
        .order_by(TrackingEvent.event_time.desc())
    )
    events = list(er.scalars().all())
    return [tracking_event_to_read(e) for e in events]
