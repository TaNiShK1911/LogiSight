"""
Invoices — upload, list, detail, anomaly analysis, mapping corrections (LogiSight).
"""

from __future__ import annotations

import os
import re
import time
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
from app.services.serialization import invoice_to_detail_read, invoice_to_header_read
from app.services.supabase_storage import upload_invoice_to_storage

router = APIRouter()

UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT", "uploads")


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


@router.post("/upload", response_model=InvoiceDetailRead, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    quote_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> InvoiceDetailRead:
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

    # Upload to Supabase Storage
    try:
        storage_url = await upload_invoice_to_storage(data, timestamped_filename, qid)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload invoice to storage: {e}"
        )

    # Create temporary local file for Veryfi extraction
    # Veryfi requires a file path, not bytes
    temp_dir = os.path.join(UPLOAD_ROOT, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, timestamped_filename)

    try:
        # Write temporary file
        with open(temp_path, "wb") as f:
            f.write(data)

        # Extract invoice data using Veryfi
        try:
            invoice_number, extracted_charges = await extract_invoice_with_veryfi(temp_path)
        except Exception as e:
            # If extraction fails, create invoice without charges
            invoice_number = f"INV-{ts}"
            extracted_charges = []
            print(f"Veryfi extraction failed: {e}")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {temp_path}: {e}")

    # Create invoice record with Supabase Storage URL
    inv = Invoice(
        quote_id=qid,
        invoice_number=invoice_number,
        invoice_date=date.today(),
        file_path=storage_url,  # Store Supabase Storage URL instead of local path
    )
    db.add(inv)
    await db.flush()

    # Map and store extracted charges
    buyer_id = int(quote.buyer_id)
    for charge in extracted_charges:
        # Map charge name to buyer's Charge Master
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
