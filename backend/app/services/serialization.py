"""
ORM → API response helpers with role-based visibility (LogiSight).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.models import (
    Airport,
    Company,
    Currency,
    Invoice,
    InvoiceCharge,
    Quote,
    QuoteCharge,
    TrackingEvent,
)
from app.schemas import (
    AirportRef,
    ChargeBasis,
    ChargeLineRead,
    CompanyRef,
    CurrencyRef,
    InvoiceChargeLineRead,
    InvoiceDetailRead,
    InvoiceHeaderRead,
    MappingTier,
    QuoteChargeSubmitItem,
    QuoteDetailRead,
    QuoteHeaderRead,
    QuoteStatus,
    TrackingEventRead,
    TrackingShipmentRead,
)


def _num(v: Decimal | float | int | None) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def _basis_str(b: str) -> str:
    return b


def quote_charge_to_line_read(qc: QuoteCharge, role: str | None) -> ChargeLineRead:
    """Apply forwarder visibility: hide mapping fields (backend_integration §4)."""
    basis = _basis_str(qc.basis)

    try:
        basis_enum = ChargeBasis(basis)
    except ValueError:
        basis_enum = ChargeBasis.PER_SHIPMENT

    if role == "forwarder":
        return ChargeLineRead(
            id=qc.id,
            raw_charge_name=qc.raw_charge_name,
            mapped_charge_id=None,
            mapped_charge_name=None,
            similarity_score=None,
            mapping_tier=MappingTier.UNMAPPED,
            low_confidence=False,
            rate=_num(qc.rate),
            basis=basis_enum,
            qty=_num(qc.qty),
            amount=_num(qc.amount),
        )

    try:
        tier = MappingTier(qc.mapping_tier)
    except ValueError:
        tier = MappingTier.UNMAPPED

    sim = float(qc.similarity_score) if qc.similarity_score is not None else None

    return ChargeLineRead(
        id=qc.id,
        raw_charge_name=qc.raw_charge_name,
        mapped_charge_id=qc.mapped_charge_id,
        mapped_charge_name=qc.mapped_charge_name,
        similarity_score=sim,
        mapping_tier=tier,
        low_confidence=qc.low_confidence,
        rate=_num(qc.rate),
        basis=basis_enum,
        qty=_num(qc.qty),
        amount=_num(qc.amount),
    )


def invoice_charge_to_line_read(ic: InvoiceCharge, role: str | None) -> InvoiceChargeLineRead:
    try:
        basis_enum = ChargeBasis(ic.basis)
    except ValueError:
        basis_enum = ChargeBasis.PER_SHIPMENT

    if role == "forwarder":
        base = ChargeLineRead(
            id=ic.id,
            raw_charge_name=ic.raw_charge_name,
            mapped_charge_id=None,
            mapped_charge_name=None,
            similarity_score=None,
            mapping_tier=MappingTier.UNMAPPED,
            low_confidence=False,
            rate=_num(ic.rate),
            basis=basis_enum,
            qty=_num(ic.qty),
            amount=_num(ic.amount),
        )
    else:
        try:
            tier = MappingTier(ic.mapping_tier)
        except ValueError:
            tier = MappingTier.UNMAPPED
        sim = float(ic.similarity_score) if ic.similarity_score is not None else None
        base = ChargeLineRead(
            id=ic.id,
            raw_charge_name=ic.raw_charge_name,
            mapped_charge_id=ic.mapped_charge_id,
            mapped_charge_name=ic.mapped_charge_name,
            similarity_score=sim,
            mapping_tier=tier,
            low_confidence=ic.low_confidence,
            rate=_num(ic.rate),
            basis=basis_enum,
            qty=_num(ic.qty),
            amount=_num(ic.amount),
        )
    d = base.model_dump()
    d["invoice_id"] = ic.invoice_id
    return InvoiceChargeLineRead(**d)


def _company_ref(c: Company | None) -> CompanyRef:
    if c is None:
        return CompanyRef(id=0, name="")
    return CompanyRef(id=int(c.id), name=c.name)


def _airport_ref(a: Airport | None) -> AirportRef:
    if a is None:
        return AirportRef(iata_code="", name="")
    return AirportRef(iata_code=a.iata_code, name=a.name)


def _currency_ref(cur: Currency | None) -> CurrencyRef:
    if cur is None:
        return CurrencyRef(short_name="")
    return CurrencyRef(short_name=cur.short_name)


def scrub_rejection_note(
    note: str | None,
    role: str | None,
    mapped_charge_names: list[str],
) -> str | None:
    """Remove Charge Master names from rejection notes for forwarders."""
    if role != "forwarder" or not note:
        return note
    out = note
    for name in mapped_charge_names:
        if not name:
            continue
        if name in out:
            out = out.replace(name, "—")
    return out if out.strip() else None


def quote_to_header_read(
    q: Quote,
    role: str | None,
    mapped_names_for_scrub: list[str] | None = None,
) -> QuoteHeaderRead:
    names = mapped_names_for_scrub or []
    rej = scrub_rejection_note(q.rejection_note, role, names)

    try:
        st = QuoteStatus(q.status)
    except ValueError:
        st = QuoteStatus.SUBMITTED

    return QuoteHeaderRead(
        id=int(q.id),
        quote_ref=q.quote_ref,
        status=st,
        rejection_note=rej,
        created_at=q.created_at,
        forwarder=_company_ref(q.forwarder),
        buyer=_company_ref(q.buyer),
        origin_airport=_airport_ref(q.origin_airport),
        destination_airport=_airport_ref(q.destination_airport),
        tracking_number=q.tracking_number,
        gross_weight=_num(q.gross_weight),
        volumetric_weight=_num(q.volumetric_weight),
        chargeable_weight=_num(q.chargeable_weight),
        currency=_currency_ref(q.currency),
    )


def quote_to_detail_read(q: Quote, role: str | None) -> QuoteDetailRead:
    mapped_names: list[str] = []
    if q.quote_charges:
        for qc in q.quote_charges:
            if qc.mapped_charge_name:
                mapped_names.append(qc.mapped_charge_name)

    header = quote_to_header_read(q, role, mapped_names)
    lines = [quote_charge_to_line_read(qc, role) for qc in (q.quote_charges or [])]

    return QuoteDetailRead(
        **header.model_dump(),
        charges=lines,
    )


def invoice_to_header_read(inv: Invoice, role: str | None) -> InvoiceHeaderRead:
    qh = quote_to_header_read(inv.quote, role)
    return InvoiceHeaderRead(
        id=int(inv.id),
        quote_id=int(inv.quote_id),
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        file_path=inv.file_path,
        uploaded_at=inv.uploaded_at,
        quote=qh,
    )


def invoice_to_detail_read(inv: Invoice, role: str | None) -> InvoiceDetailRead:
    header = invoice_to_header_read(inv, role)
    charges = [invoice_charge_to_line_read(c, role) for c in (inv.invoice_charges or [])]
    return InvoiceDetailRead(
        **header.model_dump(),
        charges=charges,
    )


def tracking_event_to_read(ev: TrackingEvent) -> TrackingEventRead:
    return TrackingEventRead(
        id=int(ev.id),
        quote_id=int(ev.quote_id),
        event_time=ev.event_time,
        location=ev.location,
        status=ev.status,
        description=ev.description,
    )


def build_tracking_shipment(
    q: Quote,
    events: list[TrackingEvent],
) -> TrackingShipmentRead:
    origin = q.origin_airport.iata_code if q.origin_airport else ""
    dest = q.destination_airport.iata_code if q.destination_airport else ""
    sorted_ev = sorted(events, key=lambda e: e.event_time, reverse=True)
    latest = sorted_ev[0] if sorted_ev else None
    last_ts: datetime = latest.event_time if latest else q.created_at
    status = latest.status if latest else "SUBMITTED"
    fw = q.forwarder.name if q.forwarder else ""
    by = q.buyer.name if q.buyer else ""
    return TrackingShipmentRead(
        quote_id=int(q.id),
        quote_ref=q.quote_ref,
        tracking_number=q.tracking_number,
        origin=origin,
        destination=dest,
        current_status=status,
        last_event_time=last_ts,
        forwarder_name=fw,
        buyer_name=by,
    )


def submit_item_to_quote_charge_row(
    quote_id: int,
    item: QuoteChargeSubmitItem,
    mapped_id: int | None,
    mapped_name: str | None,
    tier: MappingTier,
    low_confidence: bool,
    similarity: float | None,
) -> dict:
    return {
        "quote_id": quote_id,
        "raw_charge_name": item.raw_charge_name,
        "mapped_charge_id": mapped_id,
        "mapped_charge_name": mapped_name,
        "similarity_score": similarity,
        "mapping_tier": tier.value,
        "low_confidence": low_confidence,
        "rate": item.rate,
        "basis": item.basis.value,
        "qty": item.qty,
        "amount": item.amount,
    }
