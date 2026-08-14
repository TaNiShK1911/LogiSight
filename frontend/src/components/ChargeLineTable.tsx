import { useState } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { ConfidenceBadge } from './ConfidenceBadge';
import { AnomalyFlag } from './AnomalyFlag';
import type { ChargeLineRow, AnomalyRead, Charge } from '../api/types';

interface Props {
  charges: ChargeLineRow[];
  isClient: boolean;
  showConfidence?: boolean;
  chargeMaster?: Charge[];
  onCorrectMapping?: (chargeId: string, mappedChargeId: string) => void;
  anomalies?: AnomalyRead[];
  quoteCharges?: ChargeLineRow[];
  hideMapping?: boolean; // If true, only show raw charge names (for invoices)
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function MappingDropdown({
  chargeId,
  chargeMaster,
  onSelect,
}: {
  chargeId: string;
  chargeMaster: Charge[];
  onSelect: (chargeId: string, mappedChargeId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 px-2 py-1 text-label-sm rounded border border-outline-variant bg-surface-container-high text-on-surface hover:border-slate-500 transition-colors"
      >
        Correct <ChevronDown className="w-3 h-3" />
      </button>
      {open && (
        <div className="absolute z-50 left-0 top-full mt-1 w-56 rounded-lg border border-outline-variant bg-surface-container shadow-xl overflow-hidden">
          <div className="max-h-52 overflow-y-auto">
            {chargeMaster.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  onSelect(chargeId, c.id);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-left text-body-md text-on-surface hover:bg-surface-container-high transition-colors"
              >
                <span className="text-label-sm text-outline font-mono w-10 flex-shrink-0">{c.short_name}</span>
                {c.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ChargeLineTable({
  charges,
  isClient,
  showConfidence = false,
  chargeMaster = [],
  onCorrectMapping,
  anomalies = [],
  quoteCharges = [],
  hideMapping = false,
}: Props) {
  const anomalyMap = new Map(anomalies.map((a) => [a.invoice_charge_id, a]));

  // Build quote map by mapped_charge_id
  const quoteByMappedId = new Map(quoteCharges.map((q) => [q.mapped_charge_id, q]));

  // Build quote map by raw charge name (fallback)
  const quoteByRawName = new Map(
    quoteCharges.map((q) => [q.raw_charge_name.toLowerCase().trim(), q])
  );

  // Helper to find matching quote charge
  const findQuoteCharge = (charge: ChargeLineRow) => {
    // Try mapped_charge_id first
    if (charge.mapped_charge_id) {
      const match = quoteByMappedId.get(charge.mapped_charge_id);
      if (match) return match;
    }

    // Fallback to raw name matching
    const rawKey = charge.raw_charge_name.toLowerCase().trim();
    return quoteByRawName.get(rawKey) || null;
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-surface-variant">
      <table className="w-full text-body-md">
        <thead>
          <tr className="border-b border-surface-variant bg-surface-container-low">
            {isClient && !hideMapping ? (
              <>
                <th className="px-4 py-3 text-left font-semibold text-on-surface">Charge</th>
                <th className="px-4 py-3 text-left font-semibold text-on-surface-variant text-label-sm">Forwarder Term</th>
              </>
            ) : (
              <th className="px-4 py-3 text-left font-semibold text-on-surface">Charge Name</th>
            )}
            <th className="px-4 py-3 text-right font-semibold text-on-surface">Rate</th>
            <th className="px-4 py-3 text-center font-semibold text-on-surface">Basis</th>
            <th className="px-4 py-3 text-right font-semibold text-on-surface">Qty</th>
            <th className="px-4 py-3 text-right font-semibold text-on-surface">Amount</th>
            {quoteCharges.length > 0 && (
              <th className="px-4 py-3 text-right font-semibold text-on-surface">Quoted</th>
            )}
            {showConfidence && isClient && !hideMapping && (
              <th className="px-4 py-3 text-center font-semibold text-on-surface">Confidence</th>
            )}
            {quoteCharges.length > 0 && (
              <th className="px-4 py-3 text-center font-semibold text-on-surface">Flag</th>
            )}
            {onCorrectMapping && isClient && !hideMapping && (
              <th className="px-4 py-3 text-center font-semibold text-on-surface">Action</th>
            )}
          </tr>
        </thead>
        <tbody>
          {charges.map((charge, idx) => {
            const anomaly = anomalyMap.get(charge.id);
            const quoteCharge = findQuoteCharge(charge);
            const needsReview = charge.mapping_tier === 'UNMAPPED' || charge.low_confidence;
            const rowClass =
              anomaly
                ? 'bg-red-950/20 border-l-2 border-l-red-700'
                : needsReview && isClient
                ? 'bg-amber-950/10 border-l-2 border-l-amber-700'
                : idx % 2 === 0
                ? 'bg-transparent'
                : 'bg-surface-container-lowest';

            return (
              <tr key={charge.id} className={`border-b border-surface-variant transition-colors ${rowClass}`}>
                {isClient && !hideMapping ? (
                  <>
                    <td className="px-4 py-3">
                      <span className="font-medium text-primary">
                        {charge.mapped_charge_name ?? (
                          <span className="italic text-outline">Unmapped</span>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-label-sm text-outline">{charge.raw_charge_name}</span>
                    </td>
                  </>
                ) : (
                  <td className="px-4 py-3">
                    <span className="font-medium text-primary">{charge.raw_charge_name}</span>
                  </td>
                )}
                <td className="px-4 py-3 text-right font-mono text-on-surface">
                  {(() => {
                    // Show quote rate if available, otherwise show invoice rate
                    if (quoteCharge && quoteCharge.rate !== null && quoteCharge.rate !== undefined) {
                      return fmt(quoteCharge.rate);
                    }
                    if (charge.rate !== null && charge.rate !== undefined) {
                      return fmt(charge.rate);
                    }
                    return <span className="text-outline-variant">—</span>;
                  })()}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant text-label-sm">{charge.basis || '—'}</span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-on-surface">
                  {charge.qty !== null && charge.qty !== undefined ? charge.qty : <span className="text-outline-variant">—</span>}
                </td>
                <td className="px-4 py-3 text-right font-mono font-semibold text-primary">{fmt(charge.amount)}</td>
                {quoteCharges.length > 0 && (
                  <td className="px-4 py-3 text-right font-mono text-on-surface-variant">
                    {quoteCharge ? fmt(quoteCharge.amount) : <span className="text-outline-variant">—</span>}
                  </td>
                )}
                {showConfidence && isClient && !hideMapping && (
                  <td className="px-4 py-3 text-center">
                    <ConfidenceBadge tier={charge.mapping_tier} score={charge.similarity_score} />
                  </td>
                )}
                {quoteCharges.length > 0 && (
                  <td className="px-4 py-3 text-center">
                    {anomaly ? (
                      <AnomalyFlag flagType={anomaly.flag_type} compact />
                    ) : (
                      <span className="inline-flex items-center gap-1 text-label-sm text-emerald-500">
                        <Check className="w-3 h-3" /> OK
                      </span>
                    )}
                  </td>
                )}
                {onCorrectMapping && isClient && !hideMapping && (
                  <td className="px-4 py-3 text-center">
                    {needsReview && chargeMaster.length > 0 ? (
                      <MappingDropdown
                        chargeId={charge.id}
                        chargeMaster={chargeMaster}
                        onSelect={onCorrectMapping}
                      />
                    ) : charge.mapping_tier === 'HUMAN' ? (
                      <span className="text-label-sm text-emerald-500 flex items-center gap-1 justify-center">
                        <Check className="w-3 h-3" /> Verified
                      </span>
                    ) : null}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t border-outline-variant bg-surface-container-low">
            <td colSpan={isClient && !hideMapping ? 4 : 3} className="px-4 py-3 text-body-md font-semibold text-on-surface-variant">
              Total
            </td>
            <td className="px-4 py-3" />
            <td className="px-4 py-3 text-right font-mono font-bold text-primary">
              {fmt(charges.reduce((s, c) => s + c.amount, 0))}
            </td>
            {quoteCharges.length > 0 && (
              <td className="px-4 py-3 text-right font-mono font-bold text-on-surface-variant">
                {fmt(quoteCharges.reduce((s, c) => s + c.amount, 0))}
              </td>
            )}
            {showConfidence && isClient && !hideMapping && <td />}
            {quoteCharges.length > 0 && <td />}
            {onCorrectMapping && isClient && !hideMapping && <td />}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
