import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, CheckCircle, XCircle, X, AlertCircle } from 'lucide-react';
import { getQuote, updateQuoteStatus, correctQuoteChargeMapping, getCharges } from '../api/client';
import { ChargeLineTable } from '../components/ChargeLineTable';
import { useAuth } from '../hooks/useAuth';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Pending Review', cls: 'bg-sky-900/60 text-sky-300 border-sky-800' },
  ACCEPTED: { label: 'Accepted', cls: 'bg-emerald-900/60 text-emerald-300 border-emerald-800' },
  REJECTED: { label: 'Rejected', cls: 'bg-red-900/60 text-red-300 border-red-800' },
};

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-2.5 border-b border-slate-800/60 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm text-slate-200 font-medium text-right">{value}</span>
    </div>
  );
}

export function QuoteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const isClient = user?.role === 'client';

  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectNote, setRejectNote] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: quote, isLoading } = useQuery({
    queryKey: ['quotes', Number(id)],
    queryFn: () => getQuote(Number(id)),
    enabled: !!id,
  });

  const { data: chargeMaster = [] } = useQuery({
    queryKey: ['charges'],
    queryFn: getCharges,
    enabled: isClient,
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, note }: { status: 'ACCEPTED' | 'REJECTED'; note?: string }) =>
      updateQuoteStatus(Number(id), status, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quotes', Number(id)] });
      qc.invalidateQueries({ queryKey: ['quotes'] });
      setShowRejectModal(false);
      setRejectNote('');
      setActionError(null);
    },
    onError: (err: Error) => setActionError(err.message),
  });

  const correctMutation = useMutation({
    mutationFn: ({ chargeId, mappedChargeId }: { chargeId: number; mappedChargeId: number }) =>
      correctQuoteChargeMapping(chargeId, mappedChargeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['quotes', Number(id)] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!quote) {
    return <div className="text-slate-400 py-12 text-center">Quote not found.</div>;
  }

  const sc = STATUS_CONFIG[quote.status];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/app/quotes')}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100 font-mono">{quote.quote_ref}</h1>
            <span className={`px-2.5 py-1 rounded-full border text-xs font-semibold ${sc.cls}`}>
              {sc.label}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">
            {isClient ? quote.forwarder?.name : quote.buyer?.name}
          </p>
        </div>
      </div>

      {actionError && (
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-950/60 border border-red-800">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{actionError}</p>
        </div>
      )}

      {quote.status === 'REJECTED' && quote.rejection_note && (
        <div className="p-4 rounded-lg border border-red-800 bg-red-950/20">
          <p className="text-xs font-semibold text-red-400 mb-1">REJECTION NOTE</p>
          <p className="text-sm text-red-200">{quote.rejection_note}</p>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-5">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Shipment</h2>
          <InfoRow label="Origin" value={`${quote.origin_airport?.iata_code} — ${quote.origin_airport?.name}`} />
          <InfoRow label="Destination" value={`${quote.destination_airport?.iata_code} — ${quote.destination_airport?.name}`} />
          <InfoRow label="AWB / Tracking" value={<span className="font-mono">{quote.tracking_number}</span>} />
          <InfoRow label="Currency" value={quote.currency?.short_name} />
        </div>
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Weights</h2>
          <InfoRow label="Gross Weight" value={`${quote.gross_weight} kg`} />
          <InfoRow label="Volumetric Weight" value={`${quote.volumetric_weight} kg`} />
          <InfoRow label="Chargeable Weight" value={`${quote.chargeable_weight} kg`} />
          <InfoRow label="Submitted" value={new Date(quote.created_at).toLocaleDateString()} />
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-200">
            Charge Lines
            {isClient && (
              <span className="ml-2 text-xs font-normal text-slate-500">
                — showing your Charge Master nomenclature
              </span>
            )}
          </h2>
        </div>
        <ChargeLineTable
          charges={quote.charges ?? []}
          isClient={isClient}
          showConfidence={isClient}
          chargeMaster={chargeMaster}
          onCorrectMapping={
            isClient
              ? (chargeId, mappedChargeId) =>
                  correctMutation.mutate({ chargeId, mappedChargeId })
              : undefined
          }
        />
      </div>

      {isClient && quote.status === 'SUBMITTED' && (
        <div className="flex items-center justify-end gap-4 pt-2">
          <button
            onClick={() => setShowRejectModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-red-800 text-red-400 hover:bg-red-950/30 text-sm font-semibold transition-colors"
          >
            <XCircle className="w-4 h-4" /> Reject Quote
          </button>
          <button
            onClick={() => statusMutation.mutate({ status: 'ACCEPTED' })}
            disabled={statusMutation.isPending}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            {statusMutation.isPending ? 'Accepting…' : 'Accept Quote'}
          </button>
        </div>
      )}

      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-slate-800">
              <h2 className="text-base font-semibold text-slate-100">Reject Quote</h2>
              <button
                onClick={() => { setShowRejectModal(false); setRejectNote(''); }}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-sm text-slate-400">
                Optionally provide a reason. The forwarder will see this note.
              </p>
              <textarea
                value={rejectNote}
                onChange={(e) => setRejectNote(e.target.value)}
                rows={4}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                placeholder="e.g. BAF rate exceeds agreed ceiling…"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowRejectModal(false); setRejectNote(''); }}
                  className="flex-1 py-2.5 rounded-lg border border-slate-700 text-slate-300 hover:text-slate-100 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => statusMutation.mutate({ status: 'REJECTED', note: rejectNote || undefined })}
                  disabled={statusMutation.isPending}
                  className="flex-1 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
                >
                  {statusMutation.isPending ? 'Rejecting…' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
