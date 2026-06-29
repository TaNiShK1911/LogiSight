import { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Tag,
  AlertTriangle,
  FileText,
  Zap,
  Info,
} from 'lucide-react';
import {
  getPendingHitlCheckpoints,
  resolveHitlCheckpoint,
  type HitlCheckpoint,
  type HitlGateType,
} from '../api/hitl';
import { getCharges } from '../api/client';
import type { Charge } from '../api/types';

// ── Utility helpers ───────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function timeUntil(iso: string): string {
  const delta = new Date(iso).getTime() - Date.now();
  if (delta <= 0) return 'Overdue!';
  const h = Math.floor(delta / 3_600_000);
  const m = Math.floor((delta % 3_600_000) / 60_000);
  return h > 0 ? `${h}h ${m}m remaining` : `${m}m remaining`;
}

const GATE_META: Record<HitlGateType, { label: string; color: string; icon: JSX.Element; description: string }> = {
  UNMAPPED_CHARGE: {
    label: 'Unmapped Charge',
    color: 'text-amber-400 bg-amber-900/30 border-amber-700',
    icon: <Tag className="w-4 h-4" />,
    description: 'An invoice charge could not be matched to your Charge Master. Map it manually to proceed.',
  },
  HIGH_VALUE_ANOMALY: {
    label: 'Anomaly Review',
    color: 'text-red-400 bg-red-900/30 border-red-700',
    icon: <AlertTriangle className="w-4 h-4" />,
    description: 'The Autopilot Agent detected significant billing anomalies that exceed automatic thresholds.',
  },
  DISPUTE_APPROVAL: {
    label: 'Dispute Approval',
    color: 'text-sky-400 bg-sky-900/30 border-sky-700',
    icon: <FileText className="w-4 h-4" />,
    description: 'Qwen-Max has drafted a dispute letter. Review and approve it before it is sent to the forwarder.',
  },
};

// ── Gate 1: Unmapped Charge Review ───────────────────────────────────────────

function Gate1UnmappedCharge({
  checkpoint,
  onResolved,
}: {
  checkpoint: HitlCheckpoint;
  onResolved: () => void;
}) {
  const [charges, setCharges] = useState<Charge[]>([]);
  const [selectedChargeId, setSelectedChargeId] = useState<number | undefined>();
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ctx = checkpoint.context_data as Record<string, unknown>;
  const rawName = (ctx.raw_charge_name as string) || 'Unknown charge';

  useEffect(() => {
    getCharges().then(setCharges).catch(() => {});
  }, []);

  const handleApprove = async () => {
    if (!selectedChargeId) {
      setError('Please select a charge from the master list.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await resolveHitlCheckpoint(checkpoint.id, {
        status: 'APPROVED',
        mapped_charge_id: selectedChargeId,
        reviewer_notes: notes,
      });
      onResolved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to resolve');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    setError('');
    try {
      await resolveHitlCheckpoint(checkpoint.id, {
        status: 'REJECTED',
        reviewer_notes: notes || 'Rejected: charge cannot be mapped',
      });
      onResolved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to resolve');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-amber-950/30 border border-amber-800/50 rounded-lg p-4">
        <p className="text-amber-300 text-sm font-medium mb-1">Unmapped Charge Name</p>
        <p className="text-white text-lg font-semibold font-mono">"{rawName}"</p>
        <p className="text-slate-400 text-xs mt-1">
          Invoice ID: {checkpoint.invoice_id} · Workflow: {checkpoint.workflow_id.slice(0, 8)}…
        </p>
      </div>

      <div>
        <label className="block text-sm text-slate-300 mb-2 font-medium">
          Map to Charge Master entry:
        </label>
        <select
          id={`gate1-charge-select-${checkpoint.id}`}
          value={selectedChargeId ?? ''}
          onChange={(e) => setSelectedChargeId(e.target.value ? Number(e.target.value) : undefined)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-sky-500"
        >
          <option value="">— Select a charge —</option>
          {charges.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.short_name})
            </option>
          ))}
        </select>
        {selectedChargeId && (
          <p className="text-xs text-emerald-400 mt-1.5">
            ✓ This mapping will be saved as an alias for future invoices.
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm text-slate-300 mb-1.5 font-medium">
          Notes (optional):
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. 'Carrier uses alternative name for Origin Handling'"
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm resize-none h-20 focus:outline-none focus:border-sky-500"
        />
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-3">
        <button
          id={`gate1-approve-${checkpoint.id}`}
          onClick={handleApprove}
          disabled={loading || !selectedChargeId}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <CheckCircle className="w-4 h-4" />
          {loading ? 'Saving…' : 'Approve & Map Charge'}
        </button>
        <button
          id={`gate1-reject-${checkpoint.id}`}
          onClick={handleReject}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-red-900/50 hover:text-red-300 text-slate-300 text-sm font-medium rounded-lg transition-colors border border-slate-600"
        >
          <XCircle className="w-4 h-4" />
          Reject Invoice
        </button>
      </div>
    </div>
  );
}

// ── Gate 2: High-Value Anomaly Review ────────────────────────────────────────

function Gate2AnomalyReview({
  checkpoint,
  onResolved,
}: {
  checkpoint: HitlCheckpoint;
  onResolved: () => void;
}) {
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ctx = checkpoint.context_data as Record<string, unknown>;
  const anomalies = (ctx.anomalies as Array<Record<string, unknown>>) || [];
  const summary = (ctx.summary as string) || '';
  const totalDisputed = (ctx.total_disputed_amount as number) || 0;

  const handleDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    setLoading(true);
    setError('');
    try {
      await resolveHitlCheckpoint(checkpoint.id, {
        status: decision,
        reviewer_notes: notes,
      });
      onResolved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to resolve');
    } finally {
      setLoading(false);
    }
  };

  const severityColor = (s: unknown) => {
    if (s === 'HIGH') return 'text-red-400 bg-red-900/30 border-red-700';
    if (s === 'MEDIUM') return 'text-amber-400 bg-amber-900/30 border-amber-700';
    return 'text-slate-400 bg-slate-800 border-slate-700';
  };

  return (
    <div className="space-y-4">
      <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
        <p className="text-slate-300 text-sm">{summary}</p>
        {totalDisputed > 0 && (
          <p className="text-red-400 text-sm font-semibold mt-1">
            Total disputed amount: ${totalDisputed.toFixed(2)}
          </p>
        )}
      </div>

      {anomalies.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-slate-300 font-medium">Anomaly Details:</p>
          {anomalies.map((a, i) => (
            <div key={i} className={`border rounded-lg p-3 text-sm ${severityColor(a.severity)}`}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <span className="font-semibold">{String(a.charge_name)}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${severityColor(a.severity)}`}>
                  {String(a.severity)}
                </span>
              </div>
              <p className="text-slate-300 text-xs leading-relaxed">{String(a.reasoning_explanation)}</p>
              {a.invoice_amount != null && a.quoted_amount != null && (
                <div className="flex gap-4 mt-2 text-xs text-slate-400">
                  <span>Invoiced: <span className="text-white">${Number(a.invoice_amount).toFixed(2)}</span></span>
                  <span>Quoted: <span className="text-white">${Number(a.quoted_amount).toFixed(2)}</span></span>
                  {a.variance_pct != null && (
                    <span className={Number(a.variance_pct) > 0 ? 'text-red-400' : 'text-emerald-400'}>
                      {Number(a.variance_pct) > 0 ? '+' : ''}{Number(a.variance_pct).toFixed(1)}%
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div>
        <label className="block text-sm text-slate-300 mb-1.5 font-medium">Decision Notes:</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add context for the audit trail…"
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm resize-none h-20 focus:outline-none focus:border-sky-500"
        />
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-3 flex-wrap">
        <button
          id={`gate2-dispute-${checkpoint.id}`}
          onClick={() => handleDecision('APPROVED')}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-red-700 hover:bg-red-600 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <AlertTriangle className="w-4 h-4" />
          {loading ? 'Processing…' : 'Approve for Dispute'}
        </button>
        <button
          id={`gate2-accept-${checkpoint.id}`}
          onClick={() => handleDecision('REJECTED')}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <CheckCircle className="w-4 h-4" />
          Accept Invoice As-Is
        </button>
      </div>
    </div>
  );
}

// ── Gate 3: Dispute Letter Approval ──────────────────────────────────────────

function Gate3DisputeApproval({
  checkpoint,
  onResolved,
}: {
  checkpoint: HitlCheckpoint;
  onResolved: () => void;
}) {
  const ctx = checkpoint.context_data as Record<string, unknown>;
  const initialLetter = (ctx.letter_text as string) || '';
  const [letterText, setLetterText] = useState(initialLetter);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSend = async () => {
    setLoading(true);
    setError('');
    try {
      await resolveHitlCheckpoint(checkpoint.id, {
        status: 'APPROVED',
        updated_letter_text: letterText !== initialLetter ? letterText : undefined,
        reviewer_notes: notes,
      });
      onResolved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to resolve');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    setError('');
    try {
      await resolveHitlCheckpoint(checkpoint.id, {
        status: 'REJECTED',
        reviewer_notes: notes || 'Dispute letter rejected — issue resolved separately',
      });
      onResolved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to resolve');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-sky-950/30 border border-sky-800/50 rounded-lg p-3">
        <div className="flex items-center gap-2 text-sky-300 text-sm mb-1">
          <Zap className="w-3.5 h-3.5" />
          <span className="font-medium">Generated by Qwen-Max</span>
        </div>
        <p className="text-slate-400 text-xs">
          You can edit the letter before approving. Your edits will be saved.
        </p>
      </div>

      <div>
        <label className="block text-sm text-slate-300 mb-1.5 font-medium">
          Dispute Letter (editable):
        </label>
        <textarea
          id={`gate3-letter-${checkpoint.id}`}
          value={letterText}
          onChange={(e) => setLetterText(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-3 text-slate-100 text-sm resize-y min-h-48 font-mono leading-relaxed focus:outline-none focus:border-sky-500"
        />
        {letterText !== initialLetter && (
          <p className="text-xs text-amber-400 mt-1">⚠ You have modified the letter from the AI draft.</p>
        )}
      </div>

      <div>
        <label className="block text-sm text-slate-300 mb-1.5 font-medium">
          Approval Notes (optional):
        </label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add a note for the audit trail…"
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-sky-500"
        />
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-3 flex-wrap">
        <button
          id={`gate3-send-${checkpoint.id}`}
          onClick={handleSend}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <FileText className="w-4 h-4" />
          {loading ? 'Sending…' : 'Approve & Send Dispute Letter'}
        </button>
        <button
          id={`gate3-cancel-${checkpoint.id}`}
          onClick={handleReject}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-300 text-sm font-medium rounded-lg transition-colors border border-slate-600"
        >
          <XCircle className="w-4 h-4" />
          Cancel / Don't Send
        </button>
      </div>
    </div>
  );
}

// ── Checkpoint Card ───────────────────────────────────────────────────────────

function CheckpointCard({
  checkpoint,
  onResolved,
}: {
  checkpoint: HitlCheckpoint;
  onResolved: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const meta = GATE_META[checkpoint.gate_type];
  const isOverdue = new Date(checkpoint.escalate_after) <= new Date();

  return (
    <div className={`rounded-xl border bg-slate-900 overflow-hidden ${isOverdue ? 'border-red-700' : 'border-slate-700'}`}>
      {/* Header */}
      <button
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-800/50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${meta.color}`}>
          {meta.icon}
          {meta.label}
        </span>
        <span className="text-slate-300 text-sm">
          Invoice #{checkpoint.invoice_id}
        </span>
        <div className="ml-auto flex items-center gap-3">
          <span className={`flex items-center gap-1 text-xs ${isOverdue ? 'text-red-400' : 'text-slate-500'}`}>
            <Clock className="w-3.5 h-3.5" />
            {timeUntil(checkpoint.escalate_after)}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-800">
          {/* Gate description */}
          <div className="flex items-start gap-2 py-3 mb-1">
            <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
            <p className="text-slate-400 text-sm">{meta.description}</p>
          </div>

          {/* Gate-specific panel */}
          {checkpoint.gate_type === 'UNMAPPED_CHARGE' && (
            <Gate1UnmappedCharge checkpoint={checkpoint} onResolved={onResolved} />
          )}
          {checkpoint.gate_type === 'HIGH_VALUE_ANOMALY' && (
            <Gate2AnomalyReview checkpoint={checkpoint} onResolved={onResolved} />
          )}
          {checkpoint.gate_type === 'DISPUTE_APPROVAL' && (
            <Gate3DisputeApproval checkpoint={checkpoint} onResolved={onResolved} />
          )}

          {/* Metadata footer */}
          <div className="mt-4 pt-3 border-t border-slate-800 flex flex-wrap gap-4 text-xs text-slate-500">
            <span>Created: {formatDateTime(checkpoint.created_at)}</span>
            <span>Escalates: {formatDateTime(checkpoint.escalate_after)}</span>
            <span className="font-mono">Workflow: {checkpoint.workflow_id.slice(0, 12)}…</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function PendingReviews() {
  const [checkpoints, setCheckpoints] = useState<HitlCheckpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const fetchCheckpoints = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getPendingHitlCheckpoints();
      setCheckpoints(data);
      setLastRefresh(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load pending reviews');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCheckpoints();
  }, [fetchCheckpoints]);

  const handleResolved = () => {
    // Refresh list after a checkpoint is actioned
    setTimeout(fetchCheckpoints, 500);
  };

  // Group by gate type for organised display
  const byGate = {
    UNMAPPED_CHARGE: checkpoints.filter((c) => c.gate_type === 'UNMAPPED_CHARGE'),
    HIGH_VALUE_ANOMALY: checkpoints.filter((c) => c.gate_type === 'HIGH_VALUE_ANOMALY'),
    DISPUTE_APPROVAL: checkpoints.filter((c) => c.gate_type === 'DISPUTE_APPROVAL'),
  };

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-orange-500/20 border border-orange-500/30 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-orange-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">Pending Reviews</h1>
            <p className="text-sm text-slate-400">
              Human-in-the-Loop checkpoints from the Autopilot Agent
            </p>
          </div>
        </div>
        <button
          id="pending-reviews-refresh"
          onClick={fetchCheckpoints}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Last refresh */}
      <p className="text-xs text-slate-600 mb-4">
        Last refreshed: {lastRefresh.toLocaleTimeString()}
      </p>

      {error && (
        <div className="bg-red-950/50 border border-red-700 rounded-lg px-4 py-3 text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      {loading && checkpoints.length === 0 && (
        <div className="flex items-center justify-center py-20 text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          Loading pending reviews…
        </div>
      )}

      {!loading && checkpoints.length === 0 && !error && (
        <div className="text-center py-20">
          <CheckCircle className="w-12 h-12 text-emerald-500/50 mx-auto mb-4" />
          <p className="text-slate-400 text-lg font-medium">All clear!</p>
          <p className="text-slate-500 text-sm mt-1">
            No pending reviews. The Autopilot Agent is operating autonomously.
          </p>
        </div>
      )}

      {checkpoints.length > 0 && (
        <div className="space-y-6">
          {/* HITL-1: Unmapped Charges */}
          {byGate.UNMAPPED_CHARGE.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4" />
                Unmapped Charges ({byGate.UNMAPPED_CHARGE.length})
              </h2>
              <div className="space-y-3">
                {byGate.UNMAPPED_CHARGE.map((cp) => (
                  <CheckpointCard key={cp.id} checkpoint={cp} onResolved={handleResolved} />
                ))}
              </div>
            </section>
          )}

          {/* HITL-2: Anomaly Reviews */}
          {byGate.HIGH_VALUE_ANOMALY.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Anomaly Reviews ({byGate.HIGH_VALUE_ANOMALY.length})
              </h2>
              <div className="space-y-3">
                {byGate.HIGH_VALUE_ANOMALY.map((cp) => (
                  <CheckpointCard key={cp.id} checkpoint={cp} onResolved={handleResolved} />
                ))}
              </div>
            </section>
          )}

          {/* HITL-3: Dispute Approvals */}
          {byGate.DISPUTE_APPROVAL.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-sky-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Dispute Letters ({byGate.DISPUTE_APPROVAL.length})
              </h2>
              <div className="space-y-3">
                {byGate.DISPUTE_APPROVAL.map((cp) => (
                  <CheckpointCard key={cp.id} checkpoint={cp} onResolved={handleResolved} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
