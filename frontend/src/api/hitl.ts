/**
 * LogiSight HITL (Human-in-the-Loop) API client.
 * Calls the FastAPI /hitl/* endpoints for checkpoint management
 * and autopilot workflow triggering.
 */

import axios from 'axios';
import { supabase } from './supabase';

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8001';

// Authenticated axios instance (mirrors the one in client.ts)
const apiClient = axios.create({ baseURL: API_BASE });
apiClient.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Types ─────────────────────────────────────────────────────────────────────

export type HitlGateType =
  | 'UNMAPPED_CHARGE'
  | 'HIGH_VALUE_ANOMALY'
  | 'DISPUTE_APPROVAL';

export type HitlStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'OVERRIDDEN'
  | 'AUTO_ESCALATED';

export interface HitlCheckpoint {
  id: number;
  workflow_id: string;
  invoice_id: number;
  tenant_id: number;
  gate_type: HitlGateType;
  status: HitlStatus;
  context_data: Record<string, unknown>;
  reviewer_id: number | null;
  reviewer_decision: string | null;
  reviewer_notes: string | null;
  created_at: string;
  resolved_at: string | null;
  escalate_after: string;
}

export interface HitlResolvePayload {
  status: 'APPROVED' | 'REJECTED' | 'OVERRIDDEN';
  reviewer_notes?: string;
  mapped_charge_id?: number;
  updated_letter_text?: string;
}

export interface AutopilotTriggerPayload {
  invoice_id: number;
  quote_id: number;
}

export interface AutopilotTriggerResult {
  task_id: string;
  workflow_id: string;
  message: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

/** Fetch all PENDING HITL checkpoints for the current tenant. */
export async function getPendingHitlCheckpoints(): Promise<HitlCheckpoint[]> {
  const res = await apiClient.get<HitlCheckpoint[]>('/hitl/pending');
  return res.data;
}

/** Fetch a single HITL checkpoint by ID. */
export async function getHitlCheckpoint(id: number): Promise<HitlCheckpoint> {
  const res = await apiClient.get<HitlCheckpoint>(`/hitl/${id}`);
  return res.data;
}

/**
 * Resolve a HITL checkpoint (approve, reject, or override).
 * On APPROVED, this also resumes the Autopilot workflow.
 */
export async function resolveHitlCheckpoint(
  id: number,
  payload: HitlResolvePayload,
): Promise<{ status: string; checkpoint_id: number; decision: string; next: string }> {
  const res = await apiClient.post(`/hitl/${id}/resolve`, payload);
  return res.data;
}

/** Manually trigger the Autopilot Agent for a specific invoice. */
export async function triggerAutopilot(
  payload: AutopilotTriggerPayload,
): Promise<AutopilotTriggerResult> {
  const res = await apiClient.post<AutopilotTriggerResult>(
    '/hitl/autopilot/trigger',
    payload,
  );
  return res.data;
}
