import axios from 'axios';
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
  DashboardStats,
} from './types';

// ─── API Client ──────────────────────────────────────────────────────────────

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
});

// Attach JWT token from localStorage to every request
apiClient.interceptors.request.use((config) => {
  // Use id_token because Cognito access tokens don't contain custom attributes (role, company_id)
  const token = localStorage.getItem('logisight_id_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('logisight_access_token');
      localStorage.removeItem('logisight_id_token');
      localStorage.removeItem('logisight_refresh_token');
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ─── AUTH ─────────────────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<{
  access_token: string;
  id_token: string;
  refresh_token: string | null;
}> {
  const res = await apiClient.post('/auth/login', { email, password });
  const { access_token, id_token, refresh_token } = res.data;

  // Store tokens
  localStorage.setItem('logisight_access_token', access_token);
  if (id_token) localStorage.setItem('logisight_id_token', id_token);
  if (refresh_token) localStorage.setItem('logisight_refresh_token', refresh_token);

  return res.data;
}

export async function refreshTokens(): Promise<void> {
  const refreshToken = localStorage.getItem('logisight_refresh_token');
  if (!refreshToken) throw new Error('No refresh token');

  const res = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
  const { access_token, id_token } = res.data;

  localStorage.setItem('logisight_access_token', access_token);
  if (id_token) localStorage.setItem('logisight_id_token', id_token);
}

export function logoutUser(): void {
  localStorage.removeItem('logisight_access_token');
  localStorage.removeItem('logisight_id_token');
  localStorage.removeItem('logisight_refresh_token');
}

export function getStoredToken(): string | null {
  return localStorage.getItem('logisight_id_token');
}

// ─── AUTH / PROFILE ──────────────────────────────────────────────────────────

export async function getMe(): Promise<UserProfile | null> {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const res = await apiClient.get('/auth/me');
    return res.data;
  } catch {
    return null;
  }
}

// ─── COMPANIES ───────────────────────────────────────────────────────────────

export async function getCompanies(): Promise<Company[]> {
  const res = await apiClient.get('/companies');
  return res.data;
}

export async function createCompany(
  payload: Omit<Company, 'id' | 'is_active'> & {
    admin_email: string;
    admin_name: string;
    admin_password: string;
  },
): Promise<Company> {
  const res = await apiClient.post('/companies', payload);
  return res.data;
}

export async function updateCompanyStatus(id: string, is_active: boolean): Promise<Company> {
  const res = await apiClient.patch(`/companies/${id}/status`, { is_active });
  return res.data;
}

// ─── MASTER DATA ─────────────────────────────────────────────────────────────

export async function getAirports(): Promise<Airport[]> {
  const res = await apiClient.get('/masters/airports');
  return res.data;
}

export async function getCurrencies(): Promise<Currency[]> {
  const res = await apiClient.get('/masters/currencies');
  return res.data;
}

// ─── CHARGE MASTER ───────────────────────────────────────────────────────────

export async function getCharges(): Promise<Charge[]> {
  const res = await apiClient.get('/masters/charges');
  return res.data;
}

export async function createCharge(payload: { name: string; short_name: string }): Promise<Charge> {
  const res = await apiClient.post('/masters/charges', payload);
  return res.data;
}

export async function updateCharge(id: string, payload: Partial<Charge>): Promise<Charge> {
  const res = await apiClient.patch(`/masters/charges/${id}`, payload);
  return res.data;
}

export async function addAlias(chargeId: string, alias: string): Promise<ChargeAlias> {
  const res = await apiClient.post(`/masters/charges/${chargeId}/aliases`, { alias });
  return res.data;
}

export async function deleteAlias(chargeId: string, aliasId: string): Promise<void> {
  await apiClient.delete(`/masters/charges/${chargeId}/aliases/${aliasId}`);
}

// ─── QUOTES ──────────────────────────────────────────────────────────────────

export async function getQuotes(): Promise<QuoteHeader[]> {
  const res = await apiClient.get('/quotes');
  return res.data;
}

export async function getQuote(id: string): Promise<QuoteDetail> {
  const res = await apiClient.get(`/quotes/${id}`);
  return res.data;
}

export async function submitQuote(payload: QuoteSubmitPayload): Promise<QuoteDetail> {
  const res = await apiClient.post('/quotes', payload);
  return res.data;
}

export async function updateQuoteStatus(
  id: string,
  status: 'ACCEPTED' | 'REJECTED',
  rejection_note?: string,
): Promise<QuoteDetail> {
  const res = await apiClient.patch(`/quotes/${id}/status`, { status, rejection_note });
  return res.data;
}

export async function correctQuoteChargeMapping(chargeId: string, mapped_charge_id: string): Promise<void> {
  await apiClient.patch(`/quotes/charges/${chargeId}/mapping`, { mapped_charge_id });
}

// ─── INVOICES ────────────────────────────────────────────────────────────────

export async function getInvoices(quote_id?: string): Promise<InvoiceHeader[]> {
  const params = quote_id ? { quote_id } : {};
  const res = await apiClient.get('/invoices', { params });
  return res.data;
}

export async function getInvoice(id: string): Promise<InvoiceDetail> {
  const res = await apiClient.get(`/invoices/${id}`);
  return res.data;
}

export async function uploadInvoice(quote_id: string, file: File): Promise<InvoiceDetail> {
  const formData = new FormData();
  formData.append('quote_id', quote_id.toString());
  formData.append('file', file);

  const res = await apiClient.post('/invoices/upload', formData);
  return res.data;
}

export async function analyzeInvoice(id: string): Promise<AnomalyRead[]> {
  const res = await apiClient.post(`/invoices/${id}/analyze`);
  return res.data;
}

export async function getAnomalies(id: string): Promise<AnomalyRead[]> {
  const res = await apiClient.get(`/invoices/${id}/anomalies`);
  return res.data;
}

export async function correctInvoiceChargeMapping(chargeId: string, mapped_charge_id: string): Promise<void> {
  await apiClient.patch(`/invoices/charges/${chargeId}/mapping`, { mapped_charge_id });
}

// ─── TRACKING ────────────────────────────────────────────────────────────────

export async function getTracking(): Promise<TrackingShipment[]> {
  const res = await apiClient.get('/tracking');
  return res.data;
}

export async function getTrackingEvents(quoteId: string): Promise<TrackingEvent[]> {
  const res = await apiClient.get(`/tracking/${quoteId}/events`);
  return res.data;
}

// ─── COPILOT ─────────────────────────────────────────────────────────────────

export async function copilotQuery(question: string): Promise<{ answer: string }> {
  const res = await apiClient.post('/copilot/query', { question });
  return res.data;
}

// ─── DASHBOARD STATS ─────────────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  const res = await apiClient.get('/dashboard/stats');
  return res.data;
}
