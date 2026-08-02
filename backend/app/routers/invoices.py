"""
Invoices — upload, list, detail, anomaly analysis, mapping corrections (LogiSight).
Uses S3 for file storage (replaces Supabase Storage).
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, get_current_user, get_db
from app.models import Anomaly, Charge, ChargeAlias, Invoice, InvoiceCharge, Quote
from app.schemas import (
    AnomalyFlagType,
    AnomalyRead,
    InvoiceDetailRead,
    InvoiceHeaderRead,
    MappingCorrectionRequest,
    MappingTier,
)
from app.services.anomaly_detection import run_invoice_analysis
from app.services.charge_mapping import resolve_raw_charge_name
from app.services.invoice_extraction import extract_invoice_with_veryfi
from app.services.s3_client import generate_presigned_upload_url, upload_to_s3

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT", "uploads")


# ─── Request / Response Models ───────────────────────────────────────────────


class PresignedUploadResponse(BaseModel):
    upload_url: str
    invoice_id: int
    s3_key: str


class InvoiceStatusRead(BaseModel):
    id: int
    processing_status: str  # pending | processing | completed | failed


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:200] or "file.pdf"


async def _access_invoice(
    db: AsyncSession,
    invoice_id: int,
    current_user: CurrentUser,
) -> Invoice:
    inv = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.quote).selectinload(Quote.forwarder),
            selectinload(Invoice.quote).selectinload(Quote.buyer),
        )
    )
    row = inv.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    role = current_user.get("role")
    cid = current_user.get("company_id")
    q = row.quote
    if role == "super_admin":
        return row
    if role == "client" and cid is not None and int(q.buyer_id) == int(cid):
        return row
    if role == "forwarder" and cid is not None and int(q.forwarder_id) == int(cid):
        return row
    raise HTTPException(status_code=404, detail="Invoice not found")


async def _invoice_detail(db: AsyncSession, invoice_id: int, role: str | None) -> InvoiceDetailRead:
    full = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.invoice_charges),
            selectinload(Invoice.quote).selectinload(Quote.forwarder),
            selectinload(Invoice.quote).selectinload(Quote.buyer),
            selectinload(Invoice.quote).selectinload(Quote.origin_airport),
            selectinload(Invoice.quote).selectinload(Quote.destination_airport),
            selectinload(Invoice.quote).selectinload(Quote.currency),
        )
    )
    return invoice_to_detail_read(full.scalar_one(), role)


def _anomaly_rows(rows: list[Anomaly]) -> list[AnomalyRead]:
    return [
        AnomalyRead(
            id=int(a.id),
            invoice_id=int(a.invoice_id),
            invoice_charge_id=int(a.invoice_charge_id) if a.invoice_charge_id is not None else None,
            flag_type=AnomalyFlagType(a.flag_type),
            description=a.description,
            variance=float(a.variance) if a.variance is not None else None,
        )
        for a in rows
    ]


# ─── Import serialization helpers ────────────────────────────────────────────

from app.services.serialization import invoice_to_detail_read, invoice_to_header_read


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/upload-url", response_model=PresignedUploadResponse, status_code=status.HTTP_201_CREATED)
async def get_upload_url(
    quote_id: int = Form(...),
    filename: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PresignedUploadResponse:
    """
    Generate a pre-signed S3 URL for uploading an invoice PDF.
    Creates a pending Invoice record and returns the URL + invoice ID.
    Frontend uploads directly to S3, then the ingest Lambda processes it.
    """
    if current_user.get("role") != "forwarder":
        raise HTTPException(status_code=403, detail="Only forwarders upload invoices")

    cid = current_user.get("company_id")
    if cid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    quote = await db.get(Quote, quote_id)
    if quote is None or int(quote.forwarder_id) != int(cid):
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote.status != "ACCEPTED":
        raise HTTPException(status_code=400, detail="Quote must be ACCEPTED before uploading an invoice")

    ts = int(time.time() * 1000)
    fname = _safe_filename(filename)
    s3_key = f"invoices/tenant-{cid}/quote-{quote_id}/{ts}_{fname}"

    # Create pending invoice record
    inv = Invoice(
        quote_id=quote_id,
        invoice_number=f"PENDING-{ts}",
        invoice_date=date.today(),
        file_path="",
        s3_key=s3_key,
        processing_status="pending",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    # Generate pre-signed upload URL
    upload_url = generate_presigned_upload_url(s3_key, content_type="application/pdf")

    return PresignedUploadResponse(
        upload_url=upload_url,
        invoice_id=int(inv.id),
        s3_key=s3_key,
    )


@router.get("/{invoice_id}/status", response_model=InvoiceStatusRead)
async def get_invoice_status(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> InvoiceStatusRead:
    """Poll endpoint for invoice processing status."""
    inv = await _access_invoice(db, invoice_id, current_user)
    return InvoiceStatusRead(
        id=int(inv.id),
        processing_status=inv.processing_status or "completed",
    )


@router.post("/upload", response_model=InvoiceDetailRead, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    quote_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> InvoiceDetailRead:
    """
    Direct upload endpoint (local dev fallback + backwards compatibility).
    Uploads file to S3, runs Veryfi extraction, maps charges, stores in DB.
    """
    if current_user.get("role") != "forwarder":
        raise HTTPException(status_code=403, detail="Only forwarders upload invoices")

    cid = current_user.get("company_id")
    if cid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    try:
        qid = int(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="quote_id must be an integer") from exc

    quote = await db.get(Quote, qid)
    if quote is None or int(quote.forwarder_id) != int(cid):
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote.status != "ACCEPTED":
        raise HTTPException(status_code=400, detail="Quote must be ACCEPTED before uploading an invoice")

    ts = int(time.time() * 1000)
    fname = _safe_filename(file.filename or "invoice.pdf")
    timestamped_filename = f"{ts}_{fname}"

    # Read file data
    data = await file.read()

    # Upload to S3
    s3_key = f"invoices/tenant-{cid}/quote-{qid}/{timestamped_filename}"
    try:
        upload_to_s3(s3_key, data, content_type="application/pdf")
        storage_url = f"s3://{s3_key}"
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        # Fallback to local storage for dev
        storage_url = f"local://{timestamped_filename}"

    # Create temporary local file for Veryfi extraction
    temp_dir = os.path.join(UPLOAD_ROOT, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, timestamped_filename)

    try:
        with open(temp_path, "wb") as f:
            f.write(data)

        try:
            invoice_number, extracted_charges = await extract_invoice_with_veryfi(temp_path)
        except Exception as e:
            invoice_number = f"INV-{ts}"
            extracted_charges = []
            logger.warning(f"Veryfi extraction failed: {e}")

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")

    # Create invoice record
    inv = Invoice(
        quote_id=qid,
        invoice_number=invoice_number,
        invoice_date=date.today(),
        file_path=storage_url,
        s3_key=s3_key,
        processing_status="completed",
    )
    db.add(inv)
    await db.flush()

    # Map and store extracted charges
    buyer_id = int(quote.buyer_id)
    for charge in extracted_charges:
        mid, mname, tier, low, sim = await resolve_raw_charge_name(
            db, charge.raw_charge_name, buyer_id
        )

        ic = InvoiceCharge(
            invoice_id=int(inv.id),
            raw_charge_name=charge.raw_charge_name,
            mapped_charge_id=mid,
            mapped_charge_name=mname,
            similarity_score=sim,
            mapping_tier=tier.value,
            low_confidence=low,
            rate=charge.rate,
            basis=charge.basis,
            qty=charge.qty,
            amount=charge.amount,
        )
        db.add(ic)

    await db.commit()

    return await _invoice_detail(db, int(inv.id), current_user.get("role"))


@router.get("", response_model=list[InvoiceHeaderRead])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    quote_id: int | None = Query(None),
) -> list[InvoiceHeaderRead]:
    role = current_user.get("role")
    cid = current_user.get("company_id")

    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.quote).selectinload(Quote.forwarder),
            selectinload(Invoice.quote).selectinload(Quote.buyer),
            selectinload(Invoice.quote).selectinload(Quote.origin_airport),
            selectinload(Invoice.quote).selectinload(Quote.destination_airport),
            selectinload(Invoice.quote).selectinload(Quote.currency),
        )
        .order_by(Invoice.uploaded_at.desc())
    )
    if quote_id is not None:
        stmt = stmt.where(Invoice.quote_id == quote_id)

    r = await db.execute(stmt)
    rows = list(r.scalars().all())

    out: list[InvoiceHeaderRead] = []
    for inv in rows:
        q = inv.quote
        if role == "super_admin":
            out.append(invoice_to_header_read(inv, role))
        elif role == "client" and cid is not None and int(q.buyer_id) == int(cid):
            out.append(invoice_to_header_read(inv, role))
        elif role == "forwarder" and cid is not None and int(q.forwarder_id) == int(cid):
            out.append(invoice_to_header_read(inv, role))
    return out


@router.patch("/charges/{charge_id}/mapping", response_model=InvoiceDetailRead)
async def patch_invoice_charge_mapping(
    charge_id: int,
    body: MappingCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> InvoiceDetailRead:
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only clients may correct mappings")

    uid = current_user.get("company_id")
    if uid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    res = await db.execute(
        select(InvoiceCharge)
        .where(InvoiceCharge.id == charge_id)
        .options(selectinload(InvoiceCharge.invoice).selectinload(Invoice.quote))
    )
    ic = res.scalar_one_or_none()
    if ic is None:
        raise HTTPException(status_code=404, detail="Charge not found")

    quote = ic.invoice.quote
    if int(quote.buyer_id) != int(uid):
        raise HTTPException(status_code=404, detail="Charge not found")

    mapped = await db.get(Charge, body.mapped_charge_id)
    if mapped is None or int(mapped.company_id) != int(uid):
        raise HTTPException(status_code=400, detail="Invalid mapped_charge_id for your Charge Master")

    ic.mapped_charge_id = body.mapped_charge_id
    ic.mapped_charge_name = mapped.name
    ic.mapping_tier = MappingTier.HUMAN.value
    ic.low_confidence = False

    stmt = (
        insert(ChargeAlias)
        .values(charge_id=body.mapped_charge_id, alias=ic.raw_charge_name)
        .on_conflict_do_nothing(constraint="uq_charge_aliases_charge_id_alias")
    )
    await db.execute(stmt)
    await db.commit()

    return await _invoice_detail(db, int(ic.invoice_id), current_user.get("role"))


@router.get("/{invoice_id}/anomalies", response_model=list[AnomalyRead])
async def get_invoice_anomalies(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AnomalyRead]:
    if current_user.get("role") == "forwarder":
        raise HTTPException(status_code=403, detail="Anomalies are not visible to forwarders")

    await _access_invoice(db, invoice_id, current_user)

    r = await db.execute(select(Anomaly).where(Anomaly.invoice_id == invoice_id).order_by(Anomaly.id))
    return _anomaly_rows(list(r.scalars().all()))


@router.post("/{invoice_id}/analyze", response_model=list[AnomalyRead])
async def analyze_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AnomalyRead]:
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Only clients can run analysis")

    cid = current_user.get("company_id")
    if cid is None:
        raise HTTPException(status_code=403, detail="Company scope required")

    inv = await _access_invoice(db, invoice_id, current_user)
    if int(inv.quote.buyer_id) != int(cid):
        raise HTTPException(status_code=404, detail="Invoice not found")

    try:
        anomalies = await run_invoice_analysis(db, invoice_id)
    except ValueError as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _anomaly_rows(anomalies)


@router.get("/{invoice_id}", response_model=InvoiceDetailRead)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> InvoiceDetailRead:
    await _access_invoice(db, invoice_id, current_user)
    return await _invoice_detail(db, invoice_id, current_user.get("role"))
