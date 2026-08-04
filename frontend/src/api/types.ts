export type MappingTier = 'DICTIONARY' | 'VECTOR' | 'LLM' | 'HUMAN' | 'UNMAPPED';

export type QuoteStatus = 'SUBMITTED' | 'ACCEPTED' | 'REJECTED';

export type CompanyType = 'client' | 'forwarder';

export type UserRole = 'super_admin' | 'client' | 'forwarder';

export type ChargeBasis = 'Per KG' | 'Per Shipment' | 'Per CBM' | 'Flat Rate' | 'Per Chg Wt';

export type AnomalyFlagType =
  | 'AMOUNT_MISMATCH'
  | 'RATE_MISMATCH'
  | 'BASIS_MISMATCH'
  | 'UNEXPECTED_CHARGE'
  | 'MISSING_CHARGE'
  | 'DUPLICATE_INVOICE';

export interface Company {
  id: string;
  name: string;
  short_name: string;
  type: CompanyType;
  address?: string;
  city?: string;
  country?: string;
  is_active: boolean;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  is_admin: boolean;
  role: UserRole;
  company_id?: string;
  company_type?: CompanyType;
  company_name?: string;
}

export interface Charge {
  id: string;
  company_id: string;
  name: string;
  short_name: string;
  is_active: boolean;
  aliases: ChargeAlias[];
}

export interface ChargeAlias {
  id: string;
  charge_id: string;
  alias: string;
}

export interface ChargeLineRow {
  id: string;
  raw_charge_name: string;
  mapped_charge_id?: string | null;
  mapped_charge_name?: string | null;
  similarity_score?: number | null;
  mapping_tier: MappingTier;
  low_confidence: boolean;
  rate: number | null;
  basis: ChargeBasis | null;
  qty: number | null;
  amount: number;
}

export interface QuoteChargeLine extends ChargeLineRow {
  quote_id: string;
}

export interface InvoiceChargeLine extends ChargeLineRow {
  invoice_id: string;
}

export interface QuoteHeader {
  id: string;
  quote_ref: string;
  status: QuoteStatus;
  rejection_note?: string | null;
  created_at: string;
  forwarder: { id: string; name: string };
  buyer: { id: string; name: string };
  origin_airport: { iata_code: string; name: string };
  destination_airport: { iata_code: string; name: string };
  tracking_number: string;
  gross_weight: number;
  volumetric_weight: number;
  chargeable_weight: number;
  currency: { short_name: string };
  etd?: string | null;
  eta?: string | null;
  goods_description?: string | null;
}

export interface QuoteDetail extends QuoteHeader {
  charges: QuoteChargeLine[];
}

export interface InvoiceHeader {
  id: string;
  quote_id: string;
  invoice_number: string;
  invoice_date: string;
  file_path: string;
  uploaded_at: string;
  quote: QuoteHeader;
}

export interface InvoiceDetail extends InvoiceHeader {
  charges: InvoiceChargeLine[];
}

export interface AnomalyRead {
  id: string;
  invoice_id: string;
  invoice_charge_id: string;
  flag_type: AnomalyFlagType;
  description: string;
  variance?: number | null;
}

export interface TrackingEvent {
  id: string;
  quote_id: string;
  event_time: string;
  location: string;
  status: string;
  description: string;
}

export interface TrackingShipment {
  quote_id: string;
  quote_ref: string;
  tracking_number: string;
  origin: string;
  destination: string;
  current_status: string;
  last_event_time: string;
  forwarder_name: string;
  buyer_name: string;
}

export interface CopilotResponse {
  answer: string;
}

export interface DashboardStats {
  open_quotes: number;
  anomalies_pending: number;
  invoices_this_month: number;
  total_accepted: number;
}

export interface Airport {
  id: string;
  name: string;
  iata_code: string;
  country_id: string;
  is_active: boolean;
}

export interface Currency {
  id: string;
  name: string;
  short_name: string;
  is_active: boolean;
}

export interface QuoteSubmitPayload {
  buyer_id: string;
  origin_airport_id: string;
  destination_airport_id: string;
  tracking_number: string;
  gross_weight: number;
  volumetric_weight: number;
  chargeable_weight: number;
  currency_id: string;
  etd?: string | null;
  eta?: string | null;
  goods_description?: string | null;
  charges: {
    raw_charge_name: string;
    rate: number | null;
    basis: ChargeBasis;
    qty: number | null;
    amount: number;
  }[];
}
