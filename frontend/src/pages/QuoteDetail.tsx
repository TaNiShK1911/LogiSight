import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getQuote, updateQuoteStatus, correctQuoteChargeMapping, getCharges } from '../api/client';
import { ChargeLineTable } from '../components/ChargeLineTable';
import { useAuth } from '../hooks/useAuth';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Pending Review', cls: 'bg-surface-container-high text-on-surface' },
  ACCEPTED: { label: 'Accepted', cls: 'bg-surface-container text-on-surface-variant' },
  REJECTED: { label: 'Rejected', cls: 'bg-error-container text-on-error-container' },
};

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-4 border-b border-surface-container last:border-0">
      <span className="font-label-sm text-label-sm text-on-surface-variant">{label}</span>
      <span className="font-body-md text-body-md text-on-surface font-medium text-right">{value}</span>
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
    queryKey: ['quotes', id!],
    queryFn: () => getQuote(id!),
    enabled: !!id,
  });

  const { data: chargeMaster = [] } = useQuery({
    queryKey: ['charges'],
    queryFn: getCharges,
    enabled: isClient,
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, note }: { status: 'ACCEPTED' | 'REJECTED'; note?: string }) =>
      updateQuoteStatus(id!, status, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quotes', id!] });
      qc.invalidateQueries({ queryKey: ['quotes'] });
      setShowRejectModal(false);
      setRejectNote('');
      setActionError(null);
    },
    onError: (err: Error) => setActionError(err.message),
  });

  const correctMutation = useMutation({
    mutationFn: ({ chargeId, mappedChargeId }: { chargeId: string; mappedChargeId: string }) =>
      correctQuoteChargeMapping(chargeId, mappedChargeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['quotes', id!] }),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col w-full px-spacing-margin-desktop py-spacing-margin-desktop space-y-4">
        <div className="h-10 w-32 rounded-xl bg-surface-container-highest/50 animate-pulse mb-8" />
        <div className="h-32 w-full rounded-3xl bg-surface-container-lowest border border-surface-container shadow-sm animate-pulse" />
        <div className="grid md:grid-cols-2 gap-6">
           <div className="h-64 w-full rounded-3xl bg-surface-container-lowest border border-surface-container shadow-sm animate-pulse" />
           <div className="h-64 w-full rounded-3xl bg-surface-container-lowest border border-surface-container shadow-sm animate-pulse" />
        </div>
      </div>
    );
  }

  if (!quote) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[60vh]">
        <span className="material-symbols-outlined text-[64px] text-outline-variant mb-6">description</span>
        <h2 className="font-display-lg-mobile text-display-lg-mobile text-on-surface mb-2">Quote Not Found</h2>
        <p className="font-body-md text-body-md text-on-surface-variant mb-8">The quote you're looking for doesn't exist or you don't have access.</p>
        <button
          onClick={() => navigate('/app/quotes')}
          className="flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-on-primary font-label-sm text-label-sm transition-colors hover:bg-on-surface"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span> Back to Quotes
        </button>
      </div>
    );
  }

  const sc = STATUS_CONFIG[quote.status];

  return (
    <div className="flex flex-col w-full relative pb-10">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop mb-4">
        <button
          onClick={() => navigate('/app/quotes')}
          className="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors font-label-sm text-label-sm mb-6 w-fit"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span> Back to Quotes
        </button>
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-8">
          <div>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px]">request_quote</span> Quote Detail
            </p>
            <div className="flex items-center gap-4">
              <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none font-mono">{quote.quote_ref}</h1>
              <span className={`px-4 py-1.5 rounded-full font-label-sm text-label-sm tracking-wide ${sc.cls}`}>
                {sc.label}
              </span>
            </div>
            <p className="text-body-md text-on-surface-variant mt-4 font-medium flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">business</span>
              {isClient ? quote.forwarder?.name : quote.buyer?.name}
            </p>
          </div>
          
          {isClient && quote.status === 'SUBMITTED' && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowRejectModal(true)}
                className="flex items-center gap-2 px-6 py-3 rounded-full border border-error text-error hover:bg-error-container hover:text-on-error-container font-label-sm text-label-sm transition-all transform active:scale-95"
              >
                <span className="material-symbols-outlined text-[18px]">close</span> Reject
              </button>
              <button
                onClick={() => statusMutation.mutate({ status: 'ACCEPTED' })}
                disabled={statusMutation.isPending}
                className="flex items-center gap-2 px-6 py-3 rounded-full bg-primary hover:bg-on-surface disabled:opacity-60 text-on-primary font-label-sm text-label-sm shadow-sm transition-all transform active:scale-95"
              >
                <span className="material-symbols-outlined text-[18px]">check</span>
                {statusMutation.isPending ? 'Accepting...' : 'Accept Quote'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="px-spacing-margin-desktop space-y-6">
        {actionError && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-error-container text-on-error-container border border-error/20">
            <span className="material-symbols-outlined text-[20px] text-error">error</span>
            <p className="font-body-md text-body-md">{actionError}</p>
          </div>
        )}

        {quote.status === 'REJECTED' && quote.rejection_note && (
          <div className="bg-error-container/20 p-6 rounded-3xl border border-error/20 flex gap-4 items-start">
            <div className="w-10 h-10 rounded-full bg-error/10 flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-error text-[20px]">block</span>
            </div>
            <div>
              <p className="font-label-sm text-label-sm font-semibold text-error uppercase tracking-wider mb-1">Rejection Note</p>
              <p className="font-body-md text-body-md text-on-surface">{quote.rejection_note}</p>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm border border-surface-container">
            <div className="flex items-center gap-2 mb-6">
              <span className="material-symbols-outlined text-[20px] text-primary">local_shipping</span>
              <h2 className="font-label-sm text-label-sm font-semibold text-on-surface uppercase tracking-wider">Shipment Details</h2>
            </div>
            <InfoRow label="Origin" value={`${quote.origin_airport?.iata_code} — ${quote.origin_airport?.name}`} />
            <InfoRow label="Destination" value={`${quote.destination_airport?.iata_code} — ${quote.destination_airport?.name}`} />
            <InfoRow label="AWB / Tracking" value={<span className="font-mono bg-surface-container px-2 py-0.5 rounded text-sm">{quote.tracking_number}</span>} />
            <InfoRow label="Currency" value={<span className="font-mono bg-surface-container px-2 py-0.5 rounded text-sm">{quote.currency?.short_name}</span>} />
          </div>
          <div className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm border border-surface-container">
            <div className="flex items-center gap-2 mb-6">
              <span className="material-symbols-outlined text-[20px] text-primary">scale</span>
              <h2 className="font-label-sm text-label-sm font-semibold text-on-surface uppercase tracking-wider">Weights & Dates</h2>
            </div>
            <InfoRow label="Gross Weight" value={`${quote.gross_weight} kg`} />
            <InfoRow label="Volumetric Weight" value={`${quote.volumetric_weight} kg`} />
            <InfoRow label="Chargeable Weight" value={`${quote.chargeable_weight} kg`} />
            <InfoRow label="Submitted" value={new Date(quote.created_at).toLocaleDateString()} />
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm border border-surface-container">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[24px] text-primary">request_quote</span>
              <h2 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">
                Charge Lines
              </h2>
            </div>
            {isClient && (
              <p className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-2 bg-surface px-4 py-2 rounded-full border border-surface-container">
                <span className="material-symbols-outlined text-[16px]">info</span>
                Showing your Charge Master nomenclature
              </p>
            )}
          </div>
          
          <div className="w-full overflow-x-auto">
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
        </div>
      </div>

      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-scrim/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-3xl border border-surface-container bg-surface-container-lowest shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-6 border-b border-surface-container">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">block</span>
                </div>
                <h2 className="font-headline-md-mobile text-[20px] text-on-surface tracking-tight">Reject Quote</h2>
              </div>
              <button
                onClick={() => { setShowRejectModal(false); setRejectNote(''); }}
                className="w-10 h-10 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant flex items-center justify-center transition-colors"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <div className="p-6 space-y-6">
              <div>
                <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Rejection Reason (Optional)</label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-4 text-on-surface-variant text-[20px]">edit_note</span>
                  <textarea
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    rows={4}
                    className="w-full pl-11 pr-4 py-3 rounded-2xl border border-surface-container bg-surface text-on-surface placeholder:text-on-surface-variant/70 font-body-md focus:outline-none focus:border-error focus:ring-1 focus:ring-error transition-all resize-none"
                    placeholder="e.g. BAF rate exceeds agreed ceiling..."
                  />
                </div>
                <p className="font-label-sm text-[12px] text-on-surface-variant mt-2 ml-1">
                  The forwarder will be able to see this note.
                </p>
              </div>
              
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => { setShowRejectModal(false); setRejectNote(''); }}
                  className="flex-1 py-3 rounded-full border border-surface-container hover:bg-surface-container text-on-surface font-label-sm text-label-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => statusMutation.mutate({ status: 'REJECTED', note: rejectNote || undefined })}
                  disabled={statusMutation.isPending}
                  className="flex-1 py-3 rounded-full bg-error hover:bg-on-error-container disabled:opacity-60 text-on-error font-label-sm text-label-sm shadow-sm transition-colors flex items-center justify-center gap-2"
                >
                  {statusMutation.isPending ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Rejecting...
                    </>
                  ) : (
                    'Confirm Rejection'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
