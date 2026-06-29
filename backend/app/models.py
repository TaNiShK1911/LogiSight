"""
SQLAlchemy 2.0 async ORM models for LogiSight.
Schema aligns with Supabase Postgres tables and backend_integration.md contracts.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
import enum
import uuid as _uuid_module


class Company(Base):
    """Tenant company (client or forwarder)."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # 'client' | 'forwarder'
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    charges: Mapped[list[Charge]] = relationship(back_populates="company")
    profiles: Mapped[list[Profile]] = relationship(back_populates="company")


class Profile(Base):
    """App profile linked to Supabase auth.users."""

    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("companies.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    role: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="client"
    )  # super_admin | client | forwarder
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company: Mapped[Company | None] = relationship(back_populates="profiles")


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    airports: Mapped[list[Airport]] = relationship(back_populates="country")


class Currency(Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    iata_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    country_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("countries.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    country: Mapped[Country | None] = relationship(back_populates="airports")


class Charge(Base):
    """Charge Master row (scoped per client company)."""

    __tablename__ = "charges"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_charges_company_id_name"),
        UniqueConstraint("company_id", "short_name", name="uq_charges_company_id_short_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company: Mapped[Company] = relationship(back_populates="charges", foreign_keys=[company_id])
    aliases: Mapped[list[ChargeAlias]] = relationship(
        back_populates="charge", cascade="all, delete-orphan"
    )


class ChargeAlias(Base):
    __tablename__ = "charge_aliases"
    __table_args__ = (UniqueConstraint("charge_id", "alias", name="uq_charge_aliases_charge_id_alias"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    charge_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("charges.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)

    charge: Mapped[Charge] = relationship(back_populates="aliases")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    forwarder_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"), nullable=False)
    quote_ref: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    origin_airport_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("airports.id"), nullable=True
    )
    destination_airport_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("airports.id"), nullable=True
    )
    tracking_number: Mapped[str] = mapped_column(Text, nullable=False)
    gross_weight: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")
    volumetric_weight: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")
    chargeable_weight: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")
    currency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("currencies.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="SUBMITTED"
    )  # SUBMITTED | ACCEPTED | REJECTED
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    etd: Mapped[date | None] = mapped_column(Date, nullable=True)
    eta: Mapped[date | None] = mapped_column(Date, nullable=True)
    goods_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    forwarder: Mapped[Company] = relationship(foreign_keys=[forwarder_id])
    buyer: Mapped[Company] = relationship(foreign_keys=[buyer_id])
    origin_airport: Mapped[Airport | None] = relationship(foreign_keys=[origin_airport_id])
    destination_airport: Mapped[Airport | None] = relationship(foreign_keys=[destination_airport_id])
    currency: Mapped[Currency | None] = relationship()
    quote_charges: Mapped[list[QuoteCharge]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )
    invoices: Mapped[list[Invoice]] = relationship(back_populates="quote")
    tracking_events: Mapped[list[TrackingEvent]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class QuoteCharge(Base):
    __tablename__ = "quote_charges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    raw_charge_name: Mapped[str] = mapped_column(Text, nullable=False)
    mapped_charge_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("charges.id"), nullable=True)
    mapped_charge_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mapping_tier: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="UNMAPPED"
    )  # DICTIONARY | VECTOR | LLM | HUMAN | UNMAPPED
    low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    basis: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="Per Shipment"
    )  # Per KG | Per Shipment | Per CBM | Flat Rate
    qty: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")

    quote: Mapped[Quote] = relationship(back_populates="quote_charges")
    mapped_charge: Mapped[Charge | None] = relationship(foreign_keys=[mapped_charge_id])


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quotes.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    quote: Mapped[Quote] = relationship(back_populates="invoices")
    invoice_charges: Mapped[list[InvoiceCharge]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    anomalies: Mapped[list[Anomaly]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceCharge(Base):
    __tablename__ = "invoice_charges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    raw_charge_name: Mapped[str] = mapped_column(Text, nullable=False)
    mapped_charge_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("charges.id"), nullable=True)
    mapped_charge_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mapping_tier: Mapped[str] = mapped_column(Text, nullable=False, server_default="UNMAPPED")
    low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    basis: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=None)  # Per KG | Per Shipment | Per CBM | Flat Rate | NULL
    qty: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")

    invoice: Mapped[Invoice] = relationship(back_populates="invoice_charges")
    mapped_charge: Mapped[Charge | None] = relationship(foreign_keys=[mapped_charge_id])


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    invoice_charge_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("invoice_charges.id"), nullable=True
    )
    flag_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    variance: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    invoice: Mapped[Invoice] = relationship(back_populates="anomalies")
    invoice_charge: Mapped[InvoiceCharge | None] = relationship()


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    location: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    quote: Mapped[Quote] = relationship(back_populates="tracking_events")


# ── Autopilot Agent Models ────────────────────────────────────────────────────


class HitlGateType(str, enum.Enum):
    """HITL gate type — determines which review panel to show."""
    UNMAPPED_CHARGE = "UNMAPPED_CHARGE"
    HIGH_VALUE_ANOMALY = "HIGH_VALUE_ANOMALY"
    DISPUTE_APPROVAL = "DISPUTE_APPROVAL"


class HitlStatus(str, enum.Enum):
    """HITL checkpoint lifecycle status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"
    AUTO_ESCALATED = "AUTO_ESCALATED"


class HitlCheckpoint(Base):
    """
    Human-in-the-Loop checkpoint created by the Autopilot Agent when it
    encounters a decision point requiring human review.
    """

    __tablename__ = "hitl_checkpoints"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    gate_type: Mapped[HitlGateType] = mapped_column(
        SAEnum(HitlGateType, name="hitl_gate_type"), nullable=False
    )
    status: Mapped[HitlStatus] = mapped_column(
        SAEnum(HitlStatus, name="hitl_status"),
        nullable=False,
        server_default=HitlStatus.PENDING.value,
    )
    context_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reviewer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reviewer_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalate_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    invoice: Mapped[Invoice] = relationship(foreign_keys=[invoice_id])


class DisputeLetter(Base):
    """
    Dispute letter draft generated by Qwen-Max, awaiting HITL-3 approval.
    """

    __tablename__ = "dispute_letters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="DRAFT"
    )  # DRAFT | APPROVED | SENT | REJECTED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invoice: Mapped[Invoice] = relationship(foreign_keys=[invoice_id])


class AuditRecord(Base):
    """
    Immutable audit trail entry written at the end of every autopilot workflow run.
    """

    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    final_status: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # approved | disputed | escalated | pending_hitl
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice: Mapped[Invoice] = relationship(foreign_keys=[invoice_id])
