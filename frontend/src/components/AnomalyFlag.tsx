import { AlertTriangle, XCircle, MinusCircle, Copy, TrendingUp, ArrowUpDown } from 'lucide-react';
import type { AnomalyFlagType } from '../api/types';

interface Props {
  flagType: AnomalyFlagType;
  description?: string;
  compact?: boolean;
}

const CONFIG: Record<
  AnomalyFlagType,
  { label: string; bg: string; text: string; border: string; Icon: React.ElementType }
> = {
  AMOUNT_MISMATCH: {
    label: 'Amount Mismatch',
    bg: 'bg-amber-950',
    text: 'text-amber-400',
    border: 'border-amber-800',
    Icon: TrendingUp,
  },
  RATE_MISMATCH: {
    label: 'Rate Mismatch',
    bg: 'bg-amber-950',
    text: 'text-amber-400',
    border: 'border-amber-800',
    Icon: ArrowUpDown,
  },
  BASIS_MISMATCH: {
    label: 'Basis Mismatch',
    bg: 'bg-amber-950',
    text: 'text-amber-400',
    border: 'border-amber-800',
    Icon: AlertTriangle,
  },
  UNEXPECTED_CHARGE: {
    label: 'Unexpected Charge',
    bg: 'bg-red-950',
    text: 'text-red-400',
    border: 'border-red-800',
    Icon: XCircle,
  },
  MISSING_CHARGE: {
    label: 'Missing Charge',
    bg: 'bg-slate-800',
    text: 'text-slate-400',
    border: 'border-slate-600',
    Icon: MinusCircle,
  },
  DUPLICATE_INVOICE: {
    label: 'Duplicate Invoice',
    bg: 'bg-red-950',
    text: 'text-red-400',
    border: 'border-red-800',
    Icon: Copy,
  },
};

export function AnomalyFlag({ flagType, description, compact = false }: Props) {
  const c = CONFIG[flagType];
  const Icon = c.Icon;

  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${c.bg} ${c.text} ${c.border}`}>
        <Icon className="w-3 h-3" />
        {c.label}
      </span>
    );
  }

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${c.bg} ${c.border}`}>
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${c.text}`} />
      <div>
        <p className={`text-sm font-semibold ${c.text}`}>{c.label}</p>
        {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
      </div>
    </div>
  );
}
