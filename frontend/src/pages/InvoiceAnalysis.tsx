import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Zap, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { getInvoice, analyzeInvoice, getAnomalies, getCharges, correctInvoiceChargeMapping, getQuote } from '../api/client';
import { ChargeLineTable } from '../components/ChargeLineTable';
import { AnomalyFlag } from '../components/AnomalyFlag';
import { VarianceComparison } from '../components/VarianceComparison';
import { useAuth } from '../hooks/useAuth';
import type { ChargeLineRow } from '../api/types';

export function InvoiceAnalysis() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const isClient = user?.role === 'client';

  const [analysed, setAnalysed] = useState(false);

  const { data: invoice, isLoading: invLoading } = useQuery({
    queryKey: ['invoices', Number(id)],
    queryFn: () => getInvoice(Number(id)),
    enabled: !!id,
  });

  const { data: chargeMaster = [] } = useQuery({
    queryKey: ['charges'],
    queryFn: getCharges,
    enabled: isClient,
  });

  const { data: quoteDetail } = useQuery({
    queryKey: ['quotes', invoice?.quote_id],
    queryFn: () => getQuote(invoice!.quote_id),
    enabled: !!invoice?.quote_id && isClient,
  });

  const { data: anomalies = [], refetch: refetchAnomalies } = useQuery({
    queryKey: ['anomalies', Number(id)],
    queryFn: () => getAnomalies(Number(id)),
    enabled: analysed,
  });

  const analyseMutation = useMutation({
    mutationFn: () => analyzeInvoice(Number(id)),
    onSuccess: async () => {
      setAnalysed(true);
      await refetchAnomalies();
    },
  });

  const correctMutation = useMutation({
    mutationFn: ({ chargeId, mappedChargeId }: { chargeId: number; mappedChargeId: number }) =>
      correctInvoiceChargeMapping(chargeId, mappedChargeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices', Number(id)] }),
  });

  if (invLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!invoice) {
    return <div className="text-slate-400 py-12 text-center">Invoice not found.</div>;
  }

  const awbNumber = invoice.quote?.tracking_number || '';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/app/invoices')}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-100 font-mono">{invoice.invoice_number}</h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Quote: <span className="font-mono">{invoice.quote?.quote_ref}</span>
                {' · '}{invoice.invoice_date}
              </p>
            </div>
            {isClient && (
              <button
                onClick={() => analyseMutation.mutate()}
                disabled={analyseMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-60 text-white text-sm font-semibold transition-colors shadow-lg shadow-sky-500/20"
              >
                <Zap className={`w-4 h-4 ${analyseMutation.isPending ? 'animate-pulse' : ''}`} />
                {analyseMutation.isPending ? 'Analysing…' : 'Analyse Invoice'}
              </button>
            )}
          </div>
        </div>
      </div>

      {analysed && isClient && quoteDetail && (
        <VarianceComparison
          awbNumber={awbNumber}
          quoteCharges={quoteDetail.charges as any ?? []}
          invoiceCharges={invoice.charges as any ?? []}
          anomalies={anomalies as any}
          currencySymbol="$"
        />
      )}

      {analysed && anomalies.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-200">
              {anomalies.length} Anomal{anomalies.length === 1 ? 'y' : 'ies'} Detected
            </h2>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {anomalies.map((a) => (
              <AnomalyFlag key={a.id} flagType={a.flag_type} description={a.description} />
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Invoice Charges ({invoice.charges?.length ?? 0})
        </h2>
        {invoice.charges && invoice.charges.length > 0 ? (
          <ChargeLineTable
            charges={invoice.charges as ChargeLineRow[]}
            isClient={isClient}
            showConfidence={false}
            chargeMaster={chargeMaster}
            anomalies={analysed ? anomalies : []}
            quoteCharges={analysed && quoteDetail ? (quoteDetail.charges as ChargeLineRow[]) : []}
            hideMapping={true}
          />
        ) : (
          <div className="p-8 text-center text-slate-500 border border-slate-800 rounded-lg bg-slate-900/40">
            No charges extracted from this invoice.
          </div>
        )}
      </div>

    </div>
  );
}
