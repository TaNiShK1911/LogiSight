"""
Pydantic request/response models for LogiSight — aligned with frontend/backend_integration.md.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Enums (backend_integration.md §2) ---


class MappingTier(str, Enum):
    DICTIONARY = "DICTIONARY"
    VECTOR = "VECTOR"
    LLM = "LLM"
    HUMAN = "HUMAN"
    UNMAPPED = "UNMAPPED"


class ChargeBasis(str, Enum):
    PER_KG = "Per KG"
    PER_SHIPMENT = "Per Shipment"
    PER_CBM = "Per CBM"
    FLAT_RATE = "Flat Rate"
    PER_CHG_WT = "Per Chg Wt"


class QuoteStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class AnomalyFlagType(str, Enum):
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    RATE_MISMATCH = "RATE_MISMATCH"
    BASIS_MISMATCH = "BASIS_MISMATCH"
    UNEXPECTED_CHARGE = "UNEXPECTED_CHARGE"
    MISSING_CHARGE = "MISSING_CHARGE"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    CLIENT = "client"
    FORWARDER = "forwarder"


class CompanyType(str, Enum):
    CLIENT = "client"
    FORWARDER = "forwarder"


# --- Nested refs (QuoteDetail) ---


class CompanyRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AirportRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iata_code: str
    name: str


class CurrencyRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_name: str


# --- Company ---


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str
    type: Literal["client", "forwarder"]
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_active: bool


class CompanyCreate(BaseModel):
    """Payload for creating a company (used with POST /companies in later phases)."""

    name: str
    short_name: str
    type: Literal["client", "forwarder"]
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class CompanyCreateWithAdmin(CompanyCreate):
    """POST /companies — first admin user (Supabase Auth + profiles)."""

    admin_email: str
    admin_name: str
    admin_password: str


class CompanyStatusPatch(BaseModel):
    """PATCH /companies/{id}/status"""

    is_active: bool


class CompanyUserCreate(BaseModel):
    """POST /companies/{id}/users"""

    email: str
    password: str
    name: str
    is_admin: bool = False


class ProfileAdminPatch(BaseModel):
    """PATCH /users/{user_id}/admin"""

    is_admin: bool


# --- Charge lines & Quote ---


class ChargeLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_charge_name: str
    mapped_charge_id: Optional[int] = None
    mapped_charge_name: Optional[str] = None
    similarity_score: Optional[float] = None
    mapping_tier: MappingTier
    low_confidence: bool
    rate: float | None
    basis: ChargeBasis | None
    qty: float | None
    amount: float


class QuoteHeaderRead(BaseModel):
    """Quote header without charge lines (nested under invoices, list views)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_ref: str
    status: QuoteStatus
    rejection_note: Optional[str] = None
    created_at: datetime
    forwarder: CompanyRef
    buyer: CompanyRef
    origin_airport: AirportRef
    destination_airport: AirportRef
    tracking_number: str
    gross_weight: float
    volumetric_weight: float
    chargeable_weight: float
    currency: CurrencyRef
    etd: Optional[date] = None
    eta: Optional[date] = None
    goods_description: Optional[str] = None


class QuoteDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_ref: str
    status: QuoteStatus
    rejection_note: Optional[str] = None
    created_at: datetime
    forwarder: CompanyRef
    buyer: CompanyRef
    origin_airport: AirportRef
    destination_airport: AirportRef
    tracking_number: str
    gross_weight: float
    volumetric_weight: float
    chargeable_weight: float
    currency: CurrencyRef
    etd: Optional[date] = None
    eta: Optional[date] = None
    goods_description: Optional[str] = None
    charges: list[ChargeLineRead]


class QuoteChargeSubmitItem(BaseModel):
    """Single charge line in POST /quotes body (frontend QuoteSubmitPayload.charges)."""

    raw_charge_name: str
    rate: float | None = None
    basis: ChargeBasis
    qty: float | None = None
    amount: float


class QuoteSubmitPayload(BaseModel):
    """Request body for POST /quotes (mapping pipeline)."""

    buyer_id: int
    origin_airport_id: int
    destination_airport_id: int
    tracking_number: str
    gross_weight: float
    volumetric_weight: float
    chargeable_weight: float
    currency_id: int
    etd: Optional[date] = None
    eta: Optional[date] = None
    goods_description: Optional[str] = None
    charges: list[QuoteChargeSubmitItem]


class QuoteStatusUpdate(BaseModel):
    """PATCH /quotes/{id}/status"""

    status: QuoteStatus
    rejection_note: Optional[str] = None


class QuoteClientStatusUpdate(BaseModel):
    """Client accept/reject only."""

    status: Literal[QuoteStatus.ACCEPTED, QuoteStatus.REJECTED]
    rejection_note: Optional[str] = None


class MappingCorrectionRequest(BaseModel):
    """PATCH .../charges/{id}/mapping"""

    mapped_charge_id: int


# --- Invoice (InvoiceDetailRead referenced in backend_integration.md §3) ---


class InvoiceChargeLineRead(ChargeLineRead):
    """Invoice charge line includes invoice_id (frontend InvoiceChargeLine)."""

    invoice_id: int


class InvoiceHeaderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    invoice_number: str
    invoice_date: date
    file_path: str
    uploaded_at: datetime
    quote: QuoteHeaderRead


class InvoiceDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    invoice_number: str
    invoice_date: date
    file_path: str
    uploaded_at: datetime
    quote: QuoteHeaderRead
    charges: list[InvoiceChargeLineRead]


# --- Anomalies ---


class AnomalyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    invoice_charge_id: Optional[int] = None
    flag_type: AnomalyFlagType
    description: str
    variance: Optional[float] = None


# --- Tracking ---


class TrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    event_time: datetime
    location: str
    status: str
    description: str


class TrackingShipmentRead(BaseModel):
    quote_id: int
    quote_ref: str
    tracking_number: str
    origin: str
    destination: str
    current_status: str
    last_event_time: datetime
    forwarder_name: str
    buyer_name: str


# --- Copilot ---


class CopilotQueryRequest(BaseModel):
    question: str


class CopilotQueryResponse(BaseModel):
    answer: str


# --- Masters / Charge Master (frontend types.ts) ---


class ChargeAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    charge_id: int
    alias: str


class ChargeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    short_name: str
    is_active: bool
    aliases: list[ChargeAliasRead] = Field(default_factory=list)


class ChargeCreate(BaseModel):
    name: str
    short_name: str


class ChargeUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    is_active: Optional[bool] = None


class ChargeAliasCreate(BaseModel):
    alias: str


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str
    is_active: bool


class CurrencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str
    is_active: bool


class AirportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iata_code: str
    country_id: Optional[int] = None
    is_active: bool


class CountryCreate(BaseModel):
    name: str
    short_name: str


class CountryPatch(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    is_active: Optional[bool] = None


class CurrencyCreate(BaseModel):
    name: str
    short_name: str


class CurrencyPatch(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    is_active: Optional[bool] = None


class AirportCreate(BaseModel):
    name: str
    iata_code: str
    country_id: Optional[int] = None


class AirportPatch(BaseModel):
    name: Optional[str] = None
    iata_code: Optional[str] = None
    country_id: Optional[int] = None
    is_active: Optional[bool] = None


# --- Profiles / auth (Supabase-aligned) ---


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: Optional[int] = None
    name: str
    role: UserRole
    is_admin: bool
    is_active: bool


class TokenResponse(BaseModel):
    """Reserved for future auth endpoints; primary auth is Supabase JWT."""

    access_token: str
    token_type: str = "bearer"
