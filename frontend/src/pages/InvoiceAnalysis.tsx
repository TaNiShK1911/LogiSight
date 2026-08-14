import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
    queryKey: ['invoices', id!],
    queryFn: () => getInvoice(id!),
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
    queryKey: ['anomalies', id!],
    queryFn: () => getAnomalies(id!),
    enabled: analysed,
  });

  const analyseMutation = useMutation({
    mutationFn: () => analyzeInvoice(id!),
    onSuccess: async () => {
      setAnalysed(true);
      await refetchAnomalies();
    },
  });

  const correctMutation = useMutation({
    mutationFn: ({ chargeId, mappedChargeId }: { chargeId: string; mappedChargeId: string }) =>
      correctInvoiceChargeMapping(chargeId, mappedChargeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices', id!] }),
  });

  if (invLoading) {
    return (
      <div className="flex flex-col w-full px-spacing-margin-desktop py-spacing-margin-desktop space-y-4">
        <div className="h-10 w-32 rounded-xl bg-surface-container-highest/50 animate-pulse mb-8" />
        <div className="h-32 w-full rounded-3xl bg-surface-container-lowest border border-surface-container shadow-sm animate-pulse" />
        <div className="h-64 w-full rounded-3xl bg-surface-container-lowest border border-surface-container shadow-sm animate-pulse" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[60vh]">
        <span className="material-symbols-outlined text-[64px] text-outline-variant mb-6">receipt_long</span>
        <h2 className="font-display-lg-mobile text-display-lg-mobile text-on-surface mb-2">Invoice Not Found</h2>
        <p className="font-body-md text-body-md text-on-surface-variant mb-8">The invoice you're looking for doesn't exist or you don't have access.</p>
        <button
          onClick={() => navigate('/app/invoices')}
          className="flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-on-primary font-label-sm text-label-sm transition-colors hover:bg-on-surface"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span> Back to Invoices
        </button>
      </div>
    );
  }

  const awbNumber = invoice.quote?.tracking_number || '';

  return (
    <div className="flex flex-col w-full relative pb-10">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop mb-4">
        <button
          onClick={() => navigate('/app/invoices')}
          className="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors font-label-sm text-label-sm mb-6 w-fit"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span> Back to Invoices
        </button>
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-8">
          <div>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px]">receipt</span> Invoice
            </p>
            <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none font-mono">{invoice.invoice_number}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-3 font-body-md text-body-md text-on-surface-variant">
              <span>Quote: <span className="font-mono text-on-surface">{invoice.quote?.quote_ref}</span></span>
              <span className="text-outline-variant">•</span>
              <span>{invoice.invoice_date}</span>
            </div>
          </div>
          {isClient && (
            <button
              onClick={() => analyseMutation.mutate()}
              disabled={analyseMutation.isPending || analysed}
              className={`flex items-center gap-2 px-6 py-3 rounded-full font-label-sm text-label-sm transition-all shadow-sm transform active:scale-95 ${
                analysed 
                  ? 'bg-surface-container text-on-surface-variant cursor-default' 
                  : 'bg-primary text-on-primary hover:shadow-md'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">
                {analysed ? 'check_circle' : (analyseMutation.isPending ? 'hourglass_top' : 'magic_button')}
              </span>
              {analysed ? 'Analysis Complete' : (analyseMutation.isPending ? 'Analysing...' : 'Analyse Invoice')}
            </button>
          )}
        </div>
      </div>

      <div className="px-spacing-margin-desktop space-y-6">
        {analysed && isClient && quoteDetail && (
          <div className="bg-surface-container-lowest rounded-3xl p-6 shadow-sm border border-surface-container">
            <VarianceComparison
              awbNumber={awbNumber}
              quoteCharges={quoteDetail.charges as any ?? []}
              invoiceCharges={invoice.charges as any ?? []}
              anomalies={anomalies as any}
              currencySymbol="$"
            />
          </div>
        )}

        {analysed && anomalies.length > 0 && (
          <div className="bg-error-container/20 rounded-3xl p-6 border border-error/20">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-[24px] text-error">warning</span>
              <h2 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">
                {anomalies.length} Anomal{anomalies.length === 1 ? 'y' : 'ies'} Detected
              </h2>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {anomalies.map((a) => (
                <AnomalyFlag key={a.id} flagType={a.flag_type} description={a.description} />
              ))}
            </div>
          </div>
        )}

        <div className="bg-surface-container-lowest rounded-3xl p-6 shadow-sm border border-surface-container">
          <div className="flex items-center gap-3 mb-6">
            <span className="material-symbols-outlined text-[24px] text-primary">list_alt</span>
            <h2 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">
              Invoice Charges ({invoice.charges?.length ?? 0})
            </h2>
          </div>
          
          {invoice.charges && invoice.charges.length > 0 ? (
            <div className="w-full overflow-x-auto">
              <ChargeLineTable
                charges={invoice.charges as ChargeLineRow[]}
                isClient={isClient}
                showConfidence={false}
                chargeMaster={chargeMaster}
                anomalies={analysed ? anomalies : []}
                quoteCharges={analysed && quoteDetail ? (quoteDetail.charges as ChargeLineRow[]) : []}
                hideMapping={true}
              />
            </div>
          ) : (
            <div className="py-16 text-center rounded-2xl bg-surface/50 border border-surface-container border-dashed">
              <span className="material-symbols-outlined text-[40px] text-outline-variant mb-4">description</span>
              <p className="font-body-md text-body-md text-on-surface-variant max-w-md mx-auto">
                No charges extracted from this invoice yet. {isClient && !analysed ? "Run analysis to extract data." : ""}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
