"""
Quotes — list, submit (Tier-1 mapping), status updates, mapping corrections (LogiSight).
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, get_current_user, get_db, require_forwarder
from app.models import Charge, ChargeAlias, Company, Quote, QuoteCharge
from app.schemas import (
    MappingCorrectionRequest,
    MappingTier,
    QuoteClientStatusUpdate,
    QuoteDetailRead,
    QuoteHeaderRead,
    QuoteSubmitPayload,
)
from app.services.charge_mapping import resolve_raw_charge_name
from app.services.serialization import quote_to_detail_read, quote_to_header_read

router = APIRouter()


async def _load_quote(
    db: AsyncSession,
    quote_id: int,
    current_user: CurrentUser,
) -> Quote:
    q = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
            selectinload(Quote.origin_airport),
            selectinload(Quote.destination_airport),
            selectinload(Quote.currency),
            selectinload(Quote.quote_charges),
        )
    )
    quote = q.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")

    role = current_user.get("role")
    cid = current_user.get("company_id")
    if role == "super_admin":
        return quote
    if role == "client" and cid is not None and int(quote.buyer_id) == int(cid):
        return quote
    if role == "forwarder" and cid is not None and int(quote.forwarder_id) == int(cid):
        return quote
    raise HTTPException(status_code=404, detail="Quote not found")


@router.get("", response_model=list[QuoteHeaderRead])
async def list_quotes(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[QuoteHeaderRead]:
    from app.models import Quote as Q

    role = current_user.get("role")
    cid = current_user.get("company_id")

    stmt = (
        select(Q)
        .options(
            selectinload(Q.forwarder),
            selectinload(Q.buyer),
            selectinload(Q.origin_airport),
            selectinload(Q.destination_airport),
            selectinload(Q.currency),
        )
        .order_by(Q.created_at.desc())
    )
    if role == "client" and cid is not None:
        stmt = stmt.where(Q.buyer_id == cid)
    elif role == "forwarder" and cid is not None:
        stmt = stmt.where(Q.forwarder_id == cid)
    elif role == "super_admin":
        pass
    else:
        raise HTTPException(status_code=403, detail="Invalid scope")

    r = await db.execute(stmt)
    quotes = list(r.scalars().all())
    return [quote_to_header_read(q, role) for q in quotes]


@router.post("", response_model=QuoteDetailRead, status_code=status.HTTP_201_CREATED)
async def submit_quote(
    payload: QuoteSubmitPayload,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_forwarder),
) -> QuoteDetailRead:
    fid = current_user.get("company_id")
    if fid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    buyer = await db.get(Company, payload.buyer_id)
    if buyer is None or buyer.type != "client":
        raise HTTPException(status_code=400, detail="buyer_id must reference a client company")

    quote_ref = f"QR-{int(time.time() * 1000)}"
    quote = Quote(
        forwarder_id=fid,
        buyer_id=payload.buyer_id,
        quote_ref=quote_ref,
        origin_airport_id=payload.origin_airport_id,
        destination_airport_id=payload.destination_airport_id,
        tracking_number=payload.tracking_number,
        gross_weight=payload.gross_weight,
        volumetric_weight=payload.volumetric_weight,
        chargeable_weight=payload.chargeable_weight,
        currency_id=payload.currency_id,
        etd=payload.etd,
        eta=payload.eta,
        goods_description=payload.goods_description,
        status="SUBMITTED",
    )
    db.add(quote)
    await db.flush()

    for line in payload.charges:
        mid, mname, tier, low, sim = await resolve_raw_charge_name(
            db, line.raw_charge_name, payload.buyer_id
        )
        qc = QuoteCharge(
            quote_id=int(quote.id),
            raw_charge_name=line.raw_charge_name,
            mapped_charge_id=mid,
            mapped_charge_name=mname,
            similarity_score=sim,
            mapping_tier=tier.value,
            low_confidence=low,
            rate=line.rate,
            basis=line.basis.value,
            qty=line.qty,
            amount=line.amount,
        )
        db.add(qc)

    await db.commit()

    q2 = await db.execute(
        select(Quote)
        .where(Quote.id == quote.id)
        .options(
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
            selectinload(Quote.origin_airport),
            selectinload(Quote.destination_airport),
            selectinload(Quote.currency),
            selectinload(Quote.quote_charges),
        )
    )
    full = q2.scalar_one()
    return quote_to_detail_read(full, current_user.get("role"))


@router.patch("/charges/{charge_id}/mapping", response_model=QuoteDetailRead)
async def patch_quote_charge_mapping(
    charge_id: int,
    body: MappingCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> QuoteDetailRead:
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only clients may correct mappings")

    cid = current_user.get("company_id")
    if cid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    res = await db.execute(
        select(QuoteCharge)
        .where(QuoteCharge.id == charge_id)
        .options(selectinload(QuoteCharge.quote))
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Charge not found")

    quote = row.quote
    if int(quote.buyer_id) != int(cid):
        raise HTTPException(status_code=404, detail="Charge not found")

    mapped = await db.get(Charge, body.mapped_charge_id)
    if mapped is None or int(mapped.company_id) != int(cid):
        raise HTTPException(status_code=400, detail="Invalid mapped_charge_id for your Charge Master")

    row.mapped_charge_id = body.mapped_charge_id
    row.mapped_charge_name = mapped.name
    row.mapping_tier = MappingTier.HUMAN.value
    row.low_confidence = False

    from sqlalchemy.dialects.postgresql import insert

    stmt = (
        insert(ChargeAlias)
        .values(charge_id=body.mapped_charge_id, alias=row.raw_charge_name)
        .on_conflict_do_nothing(constraint="uq_charge_aliases_charge_id_alias")
    )
    await db.execute(stmt)

    await db.commit()

    q2 = await db.execute(
        select(Quote)
        .where(Quote.id == quote.id)
        .options(
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
            selectinload(Quote.origin_airport),
            selectinload(Quote.destination_airport),
            selectinload(Quote.currency),
            selectinload(Quote.quote_charges),
        )
    )
    return quote_to_detail_read(q2.scalar_one(), current_user.get("role"))


@router.patch("/{quote_id}/status", response_model=QuoteDetailRead)
async def patch_quote_status(
    quote_id: int,
    body: QuoteClientStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> QuoteDetailRead:
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only the client can accept or reject quotes")

    cid = current_user.get("company_id")
    if cid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    quote = await _load_quote(db, quote_id, current_user)
    if int(quote.buyer_id) != int(cid):
        raise HTTPException(status_code=404, detail="Quote not found")

    quote.status = body.status.value
    quote.rejection_note = body.rejection_note
    await db.commit()

    q2 = await db.execute(
        select(Quote)
        .where(Quote.id == quote.id)
        .options(
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
            selectinload(Quote.origin_airport),
            selectinload(Quote.destination_airport),
            selectinload(Quote.currency),
            selectinload(Quote.quote_charges),
        )
    )
    return quote_to_detail_read(q2.scalar_one(), current_user.get("role"))


@router.get("/{quote_id}", response_model=QuoteDetailRead)
async def get_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> QuoteDetailRead:
    quote = await _load_quote(db, quote_id, current_user)
    q2 = await db.execute(
        select(Quote)
        .where(Quote.id == quote.id)
        .options(
            selectinload(Quote.forwarder),
            selectinload(Quote.buyer),
            selectinload(Quote.origin_airport),
            selectinload(Quote.destination_airport),
            selectinload(Quote.currency),
            selectinload(Quote.quote_charges),
        )
    )
    return quote_to_detail_read(q2.scalar_one(), current_user.get("role"))
