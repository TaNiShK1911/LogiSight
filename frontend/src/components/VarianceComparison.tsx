import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

interface Charge {
  id: number;
  raw_charge_name: string;
  mapped_charge_id: number | null;
  mapped_charge_name: string | null;
  rate: number;
  qty: number;
  amount: number;
  basis: string;
}

interface Anomaly {
  id: number;
  flag_type: string;
  description: string;
  variance: number | null;
  invoice_charge_id: number | null;
}

interface VarianceComparisonProps {
  awbNumber: string;
  quoteCharges: Charge[];
  invoiceCharges: Charge[];
  anomalies: Anomaly[];
  currencySymbol?: string;
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getVarianceColor(variance: number, threshold: number = 5): string {
  const absVariance = Math.abs(variance);
  if (absVariance === 0) return 'text-emerald-400';
  if (absVariance <= threshold) return 'text-yellow-400';
  return 'text-red-400';
}

function getVarianceBg(variance: number, threshold: number = 5): string {
  const absVariance = Math.abs(variance);
  if (absVariance === 0) return 'bg-emerald-950/20 border-emerald-800';
  if (absVariance <= threshold) return 'bg-yellow-950/20 border-yellow-800';
  return 'bg-red-950/20 border-red-800';
}

export function VarianceComparison({
  awbNumber,
  quoteCharges,
  invoiceCharges,
  anomalies,
  currencySymbol = '$'
}: VarianceComparisonProps) {
  // Create maps for matching by mapped_charge_id (matches backend logic)
  const quoteByMappedId = new Map<number, Charge>();
  const invoiceByMappedId = new Map<number, Charge>();

  // Fallback maps by raw charge name (for unmapped charges)
  const quoteByRawName = new Map<string, Charge>();
  const invoiceByRawName = new Map<string, Charge>();

  // Populate quote maps
  quoteCharges.forEach(c => {
    if (c.mapped_charge_id !== null) {
      quoteByMappedId.set(c.mapped_charge_id, c);
    }
    quoteByRawName.set(c.raw_charge_name.toLowerCase(), c);
  });

  // Populate invoice maps
  invoiceCharges.forEach(c => {
    if (c.mapped_charge_id !== null) {
      invoiceByMappedId.set(c.mapped_charge_id, c);
    }
    invoiceByRawName.set(c.raw_charge_name.toLowerCase(), c);
  });

  // Get anomalies by invoice charge id
  const anomalyByChargeId = new Map(
    anomalies.map(a => [a.invoice_charge_id, a])
  );

  // Calculate totals
  const quoteTotal = quoteCharges.reduce((sum, c) => sum + c.amount, 0);
  const invoiceTotal = invoiceCharges.reduce((sum, c) => sum + c.amount, 0);
  const totalVariance = invoiceTotal - quoteTotal;
  const totalVariancePct = quoteTotal > 0 ? ((totalVariance / quoteTotal) * 100) : 0;

  // Build comparison rows - only show charges that exist in BOTH quote and invoice
  const comparisonRows: Array<{
    chargeName: string;
    quoteCharge: Charge | null;
    invoiceCharge: Charge | null;
    anomaly: Anomaly | null;
  }> = [];

  // Only add invoice charges that have a matching quote charge
  invoiceCharges.forEach(invCharge => {
    // Try to find matching quote charge
    let quoteCharge: Charge | null = null;

    if (invCharge.mapped_charge_id !== null) {
      // Try to match by mapped_charge_id first
      quoteCharge = quoteByMappedId.get(invCharge.mapped_charge_id) || null;
    }

    // Fallback: match by raw charge name (handles unmapped charges or when quote was unmapped)
    if (!quoteCharge) {
      const rawKey = invCharge.raw_charge_name.toLowerCase().trim();
      quoteCharge = quoteByRawName.get(rawKey) || null;

      // Try fuzzy matching on raw names (remove common variations)
      if (!quoteCharge) {
        for (const [qRaw, qCharge] of quoteByRawName.entries()) {
          const invNorm = rawKey.replace(/\s+/g, ' ');
          const qNorm = qRaw.replace(/\s+/g, ' ');

          // Match if one contains the other or they're very similar
          if (invNorm.includes(qNorm) || qNorm.includes(invNorm)) {
            quoteCharge = qCharge;
            break;
          }
        }
      }
    }

    // Only add to comparison if charge exists in both quote and invoice
    if (quoteCharge) {
      const anomaly = anomalyByChargeId.get(invCharge.id) || null;

      comparisonRows.push({
        chargeName: invCharge.mapped_charge_name || invCharge.raw_charge_name,
        quoteCharge,
        invoiceCharge: invCharge,
        anomaly
      });
    }
  });

  // Don't add missing charges - only show what's in the invoice

  return (
    <div className="space-y-6">
      {/* AWB Number Header */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-slate-700 bg-slate-900/60">
        <div>
          <p className="text-xs text-slate-500 mb-1">Air Waybill Number</p>
          <p className="text-xl font-bold font-mono text-sky-400">{awbNumber || 'N/A'}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 mb-1">Total Variance</p>
          <p className={`text-2xl font-bold font-mono ${getVarianceColor(totalVariancePct, 5)}`}>
            {totalVariance >= 0 ? '+' : ''}{currencySymbol}{fmt(totalVariance)}
            <span className="text-sm ml-2">({totalVariancePct >= 0 ? '+' : ''}{totalVariancePct.toFixed(1)}%)</span>
          </p>
        </div>
      </div>

      {/* Variance Summary Cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
          <p className="text-xs text-slate-500 mb-1">Quote Total</p>
          <p className="text-2xl font-bold font-mono text-slate-100">{currencySymbol}{fmt(quoteTotal)}</p>
        </div>
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
          <p className="text-xs text-slate-500 mb-1">Invoice Total</p>
          <p className="text-2xl font-bold font-mono text-slate-100">{currencySymbol}{fmt(invoiceTotal)}</p>
        </div>
        <div className={`p-4 rounded-xl border ${getVarianceBg(totalVariancePct, 5)}`}>
          <p className="text-xs text-slate-500 mb-1">Variance</p>
          <p className={`text-2xl font-bold font-mono ${getVarianceColor(totalVariancePct, 5)}`}>
            {totalVariance >= 0 ? '+' : ''}{currencySymbol}{fmt(totalVariance)}
          </p>
        </div>
      </div>

      {/* Charge-by-Charge Comparison Table */}
      <div className="rounded-xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400">Charge Name</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400">Quote Amount</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400">Invoice Amount</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400">Variance</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400">Variance %</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400">Status</th>
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row, idx) => {
                const quoteAmount = row.quoteCharge?.amount || 0;
                const invoiceAmount = row.invoiceCharge?.amount || 0;
                const variance = invoiceAmount - quoteAmount;
                const variancePct = quoteAmount > 0 ? ((variance / quoteAmount) * 100) : (invoiceAmount > 0 ? 100 : 0);

                const hasIssue = row.anomaly || Math.abs(variancePct) > 5;

                return (
                  <tr
                    key={`${row.chargeName}-${idx}`}
                    className={`border-b border-slate-800/60 ${hasIssue ? 'bg-red-950/10' : ''}`}
                  >
                    <td className="px-4 py-3 font-medium text-slate-200">
                      {row.chargeName}
                      {row.anomaly && (
                        <div className="text-xs text-slate-500 mt-1">{row.anomaly.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">
                      {row.quoteCharge ? `${currencySymbol}${fmt(quoteAmount)}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">
                      {row.invoiceCharge ? `${currencySymbol}${fmt(invoiceAmount)}` : '—'}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold ${getVarianceColor(variancePct, 5)}`}>
                      {variance !== 0 ? `${variance >= 0 ? '+' : ''}${currencySymbol}${fmt(variance)}` : '—'}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold ${getVarianceColor(variancePct, 5)}`}>
                      {variance !== 0 ? `${variancePct >= 0 ? '+' : ''}${variancePct.toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {Math.abs(variancePct) > 5 ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-red-950/40 text-red-400 border border-red-800">
                          <AlertTriangle className="w-3 h-3" /> Variance
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-emerald-950/40 text-emerald-400 border border-emerald-800">
                          <CheckCircle2 className="w-3 h-3" /> OK
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
