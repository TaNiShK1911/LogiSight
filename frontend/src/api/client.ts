import axios from 'axios';
import { supabase } from './supabase';
import type {
  Company,
  Charge,
  ChargeAlias,
  QuoteHeader,
  QuoteDetail,
  QuoteSubmitPayload,
  InvoiceHeader,
  InvoiceDetail,
  AnomalyRead,
  TrackingShipment,
  TrackingEvent,
  Airport,
  Currency,
  UserProfile,
} from './types';

// ─── helpers ─────────────────────────────────────────────────────────────────

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8001';

async function myProfile() {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error('Not authenticated');

  const { data } = await supabase.from('profiles').select('*').eq('id', user.id).maybeSingle();

  // Fall back to JWT metadata if profile row is missing or has no company_id
  const meta = user.user_metadata ?? {};
  const appMeta = user.app_metadata ?? {};
  const company_id = data?.company_id ?? meta.company_id ?? appMeta.company_id ?? null;
  const role = data?.role ?? appMeta.role ?? meta.role ?? null;
  const name = data?.name ?? meta.name ?? user.email ?? '';
  const is_admin = data?.is_admin ?? meta.is_admin ?? appMeta.is_admin ?? false;

  // Auto-create profile row if it doesn't exist yet
  if (!data && company_id) {
    await supabase.from('profiles').upsert({
      id: user.id,
      company_id,
      role,
      name,
      is_admin,
    });
  }

  const profile = { ...(data ?? {}), company_id, role, name, is_admin };
  return { user, profile };
}

// ─── AUTH / PROFILE ──────────────────────────────────────────────────────────

export async function getMe(): Promise<UserProfile | null> {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;
  const { data } = await supabase.from('profiles').select('*').eq('id', user.id).maybeSingle();
  if (!data) return null;
  return {
    id: user.id,
    email: user.email ?? '',
    name: data.name,
    role: data.role,
    company_id: data.company_id,
    company_type: data.role === 'client' ? 'client' : data.role === 'forwarder' ? 'forwarder' : undefined,
    is_admin: data.is_admin,
  };
}

// ─── COMPANIES ───────────────────────────────────────────────────────────────

export async function getCompanies(): Promise<Company[]> {
  const { data, error } = await supabase.from('companies').select('*').order('name');
  if (error) throw error;
  return data ?? [];
}

export async function createCompany(
  payload: Omit<Company, 'id' | 'is_active'> & {
    admin_email: string;
    admin_name: string;
    admin_password: string;
  },
): Promise<Company> {
  const { admin_email, admin_name, admin_password, ...companyData } = payload;

  const { data: company, error: compErr } = await supabase
    .from('companies')
    .insert({ ...companyData, is_active: true })
    .select()
    .single();
  if (compErr) throw compErr;

  const { data: authData, error: authErr } = await supabase.auth.signUp({
    email: admin_email,
    password: admin_password,
    options: {
      data: {
        name: admin_name,
        role: company.type,
        company_id: company.id,
        company_type: company.type,
        company_name: company.name,
        is_admin: true,
      },
    },
  });
  if (authErr) throw authErr;

  if (authData.user) {
    await supabase.from('profiles').upsert({
      id: authData.user.id,
      company_id: company.id,
      name: admin_name,
      role: company.type,
      is_admin: true,
    });
  }

  return company;
}

export async function updateCompanyStatus(id: number, is_active: boolean): Promise<Company> {
  const { data, error } = await supabase
    .from('companies')
    .update({ is_active })
    .eq('id', id)
    .select()
    .single();
  if (error) throw error;
  return data;
}

// ─── MASTER DATA ─────────────────────────────────────────────────────────────

export async function getAirports(): Promise<Airport[]> {
  const { data, error } = await supabase
    .from('airports')
    .select('*')
    .eq('is_active', true)
    .order('iata_code');
  if (error) throw error;
  return data ?? [];
}

export async function getCurrencies(): Promise<Currency[]> {
  const { data, error } = await supabase
    .from('currencies')
    .select('*')
    .eq('is_active', true)
    .order('short_name');
  if (error) throw error;
  return data ?? [];
}

// ─── CHARGE MASTER ───────────────────────────────────────────────────────────

export async function getCharges(): Promise<Charge[]> {
  const { data, error } = await supabase
    .from('charges')
    .select('*, aliases:charge_aliases(*)')
    .order('short_name');
  if (error) throw error;
  return (data ?? []).map((c) => ({ ...c, aliases: c.aliases ?? [] }));
}

export async function createCharge(payload: { name: string; short_name: string }): Promise<Charge> {
  const { profile } = await myProfile();
  if (!profile?.company_id) throw new Error('No company associated');

  const { data, error } = await supabase
    .from('charges')
    .insert({ ...payload, company_id: profile.company_id })
    .select('*, aliases:charge_aliases(*)')
    .single();
  if (error) throw error;
  return { ...data, aliases: data.aliases ?? [] };
}

export async function updateCharge(id: number, payload: Partial<Charge>): Promise<Charge> {
  const { data, error } = await supabase
    .from('charges')
    .update(payload)
    .eq('id', id)
    .select('*, aliases:charge_aliases(*)')
    .single();
  if (error) throw error;
  return { ...data, aliases: data.aliases ?? [] };
}

export async function addAlias(chargeId: number, alias: string): Promise<ChargeAlias> {
  const { data, error } = await supabase
    .from('charge_aliases')
    .insert({ charge_id: chargeId, alias })
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function deleteAlias(_chargeId: number, aliasId: number): Promise<void> {
  const { error } = await supabase.from('charge_aliases').delete().eq('id', aliasId);
  if (error) throw error;
}

// ─── QUOTES ──────────────────────────────────────────────────────────────────

const QUOTE_SELECT = `
  *,
  forwarder:companies!quotes_forwarder_id_fkey(id, name),
  buyer:companies!quotes_buyer_id_fkey(id, name),
  origin_airport:airports!quotes_origin_airport_id_fkey(iata_code, name),
  destination_airport:airports!quotes_destination_airport_id_fkey(iata_code, name),
  currency:currencies!quotes_currency_id_fkey(short_name)
`;

export async function getQuotes(): Promise<QuoteHeader[]> {
  const { data, error } = await supabase
    .from('quotes')
    .select(QUOTE_SELECT)
    .order('created_at', { ascending: false });
  if (error) throw error;
  return (data ?? []) as unknown as QuoteHeader[];
}

export async function getQuote(id: number): Promise<QuoteDetail> {
  const { data, error } = await supabase
    .from('quotes')
    .select(`${QUOTE_SELECT}, charges:quote_charges(*)`)
    .eq('id', id)
    .single();
  if (error) throw error;
  return data as unknown as QuoteDetail;
}

export async function submitQuote(payload: QuoteSubmitPayload): Promise<QuoteDetail> {
  const { profile } = await myProfile();
  if (!profile?.company_id) throw new Error('No company associated');

  const quoteRef = `QR-${Date.now()}`;
  const { charges, ...headerPayload } = payload;

  // Insert quote header
  const { data: quote, error: qErr } = await supabase
    .from('quotes')
    .insert({ 
      ...headerPayload, 
      forwarder_id: profile.company_id, 
      quote_ref: quoteRef,
    })
    .select()
    .single();
  if (qErr) throw qErr;

  // Get buyer's charge master for mapping
  const { data: chargeMaster = [] } = await supabase
    .from('charges')
    .select('id, name, short_name, aliases:charge_aliases(alias)')
    .eq('company_id', payload.buyer_id)
    .eq('is_active', true);

  // Map each charge
  const chargeRows = charges.map((c) => {
    const rawLower = c.raw_charge_name.trim().toLowerCase();
    
    // Try to find matching charge by name, short_name, or alias
    let mapped = chargeMaster.find(
      (cm) =>
        cm.name.toLowerCase() === rawLower ||
        cm.short_name.toLowerCase() === rawLower
    );
    
    // If not found by name, check aliases
    if (!mapped) {
      mapped = chargeMaster.find((cm) =>
        cm.aliases?.some((a: any) => a.alias.toLowerCase() === rawLower)
      );
    }

    return {
      ...c,
      quote_id: quote.id,
      mapped_charge_id: mapped?.id || null,
      mapped_charge_name: mapped?.name || null,
      mapping_tier: mapped ? 'DICTIONARY' : 'UNMAPPED',
      low_confidence: !mapped,
      similarity_score: null,
    };
  });

  const { error: cErr } = await supabase.from('quote_charges').insert(chargeRows);
  if (cErr) throw cErr;

  return getQuote(quote.id);
}

export async function updateQuoteStatus(
  id: number,
  status: 'ACCEPTED' | 'REJECTED',
  rejection_note?: string,
): Promise<QuoteDetail> {
  const { error } = await supabase
    .from('quotes')
    .update({ status, rejection_note: rejection_note ?? null })
    .eq('id', id);
  if (error) throw error;
  return getQuote(id);
}

export async function correctQuoteChargeMapping(chargeId: number, mapped_charge_id: number): Promise<void> {
  const { data: charge } = await supabase
    .from('quote_charges')
    .select('raw_charge_name')
    .eq('id', chargeId)
    .maybeSingle();

  const { error } = await supabase
    .from('quote_charges')
    .update({ mapped_charge_id, mapping_tier: 'HUMAN', low_confidence: false })
    .eq('id', chargeId);
  if (error) throw error;

  if (charge?.raw_charge_name) {
    await supabase
      .from('charge_aliases')
      .upsert({ charge_id: mapped_charge_id, alias: charge.raw_charge_name }, { onConflict: 'charge_id,alias' });
  }
}

// ─── INVOICES ────────────────────────────────────────────────────────────────

const INVOICE_SELECT = `
  *,
  quote:quotes(
    id, quote_ref, tracking_number, status,
    forwarder:companies!quotes_forwarder_id_fkey(id, name),
    buyer:companies!quotes_buyer_id_fkey(id, name),
    origin_airport:airports!quotes_origin_airport_id_fkey(iata_code, name),
    destination_airport:airports!quotes_destination_airport_id_fkey(iata_code, name),
    currency:currencies!quotes_currency_id_fkey(short_name)
  )
`;

export async function getInvoices(quote_id?: number): Promise<InvoiceHeader[]> {
  let query = supabase
    .from('invoices')
    .select(INVOICE_SELECT)
    .order('uploaded_at', { ascending: false });
  if (quote_id) query = query.eq('quote_id', quote_id);
  const { data, error } = await query;
  if (error) throw error;
  return (data ?? []) as unknown as InvoiceHeader[];
}

export async function getInvoice(id: number): Promise<InvoiceDetail> {
  const { data, error } = await supabase
    .from('invoices')
    .select(`${INVOICE_SELECT}, charges:invoice_charges(*)`)
    .eq('id', id)
    .single();
  if (error) throw error;
  return data as unknown as InvoiceDetail;
}

export async function uploadInvoice(quote_id: number, file: File): Promise<InvoiceDetail> {
  // Call backend API which handles both Supabase upload AND Veryfi extraction
  const formData = new FormData();
  formData.append('quote_id', quote_id.toString());
  formData.append('file', file);

  // Don't set Content-Type manually - axios will set it automatically with boundary for FormData
  // This also ensures the Authorization header from the interceptor isn't overridden
  const res = await apiClient.post('/invoices/upload', formData);

  return res.data;
}

export async function analyzeInvoice(id: number): Promise<AnomalyRead[]> {
  // Call backend API endpoint for anomaly detection
  const res = await apiClient.post(`/invoices/${id}/analyze`);
  return res.data;
}

export async function getAnomalies(id: number): Promise<AnomalyRead[]> {
  // Call backend API endpoint for anomalies
  const res = await apiClient.get(`/invoices/${id}/anomalies`);
  return res.data;
}

export async function correctInvoiceChargeMapping(chargeId: number, mapped_charge_id: number): Promise<void> {
  const { data: charge } = await supabase
    .from('invoice_charges')
    .select('raw_charge_name')
    .eq('id', chargeId)
    .maybeSingle();

  const { error } = await supabase
    .from('invoice_charges')
    .update({ mapped_charge_id, mapping_tier: 'HUMAN', low_confidence: false })
    .eq('id', chargeId);
  if (error) throw error;

  if (charge?.raw_charge_name) {
    await supabase
      .from('charge_aliases')
      .upsert({ charge_id: mapped_charge_id, alias: charge.raw_charge_name }, { onConflict: 'charge_id,alias' });
  }
}

// ─── TRACKING ────────────────────────────────────────────────────────────────

export async function getTracking(): Promise<TrackingShipment[]> {
  const { data, error } = await supabase
    .from('quotes')
    .select(`
      id, quote_ref, tracking_number,
      forwarder:companies!quotes_forwarder_id_fkey(name),
      buyer:companies!quotes_buyer_id_fkey(name),
      origin_airport:airports!quotes_origin_airport_id_fkey(iata_code),
      destination_airport:airports!quotes_destination_airport_id_fkey(iata_code),
      tracking_events(status, event_time)
    `)
    .order('created_at', { ascending: false });
  if (error) throw error;

  return ((data ?? []) as unknown as Array<{
    id: number;
    quote_ref: string;
    tracking_number: string;
    forwarder: { name: string } | null;
    buyer: { name: string } | null;
    origin_airport: { iata_code: string } | null;
    destination_airport: { iata_code: string } | null;
    tracking_events: Array<{ status: string; event_time: string }>;
  }>).map((q) => {
    const events = (q.tracking_events ?? []).sort(
      (a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime(),
    );
    const latest = events[0];
    return {
      quote_id: q.id,
      quote_ref: q.quote_ref,
      tracking_number: q.tracking_number,
      origin: q.origin_airport?.iata_code ?? '',
      destination: q.destination_airport?.iata_code ?? '',
      current_status: latest?.status ?? 'SUBMITTED',
      last_event_time: latest?.event_time ?? '',
      forwarder_name: q.forwarder?.name ?? '',
      buyer_name: q.buyer?.name ?? '',
    };
  });
}

export async function getTrackingEvents(quoteId: number): Promise<TrackingEvent[]> {
  const { data, error } = await supabase
    .from('tracking_events')
    .select('*')
    .eq('quote_id', quoteId)
    .order('event_time', { ascending: false });
  if (error) throw error;
  return (data ?? []) as TrackingEvent[];
}

// ─── COPILOT (FastAPI proxy) ──────────────────────────────────────────────────

const apiClient = axios.create({
  baseURL: (import.meta.env.VITE_API_URL as string) || 'http://localhost:8001',
});

apiClient.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function copilotQuery(question: string): Promise<{ answer: string }> {
  const res = await apiClient.post('/copilot/query', { question });
  return res.data;
}

// ─── DASHBOARD STATS ─────────────────────────────────────────────────────────

export async function getDashboardStats() {
  const [quotes, invoices] = await Promise.all([getQuotes(), getInvoices()]);
  const now = new Date();
  return {
    open_quotes: quotes.filter((q) => q.status === 'SUBMITTED').length,
    anomalies_pending: 0,
    invoices_this_month: invoices.filter((inv) => {
      const d = new Date(inv.uploaded_at ?? inv.invoice_date);
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length,
    total_accepted: quotes.filter((q) => q.status === 'ACCEPTED').length,
  };
}
