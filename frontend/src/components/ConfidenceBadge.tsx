import type { MappingTier } from '../api/types';

interface Props {
  tier: MappingTier;
  score?: number | null;
}

const CONFIG: Record<MappingTier, { label: string; dot: string; bg: string; text: string }> = {
  DICTIONARY: {
    label: 'High Confidence',
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-950 border-emerald-800',
    text: 'text-emerald-400',
  },
  VECTOR: {
    label: '',
    dot: '',
    bg: '',
    text: '',
  },
  LLM: {
    label: 'AI Resolved',
    dot: 'bg-sky-500',
    bg: 'bg-sky-950 border-sky-800',
    text: 'text-sky-400',
  },
  HUMAN: {
    label: 'Human Verified',
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-950 border-emerald-800',
    text: 'text-emerald-400',
  },
  UNMAPPED: {
    label: 'Needs Review',
    dot: 'bg-red-500',
    bg: 'bg-red-950 border-red-800',
    text: 'text-red-400',
  },
};

function resolveConfig(tier: MappingTier, score?: number | null) {
  if (tier === 'VECTOR') {
    if (score !== undefined && score !== null) {
      if (score >= 0.85) {
        return {
          label: 'High Confidence',
          dot: 'bg-emerald-500',
          bg: 'bg-emerald-950 border-emerald-800',
          text: 'text-emerald-400',
        };
      }
      if (score >= 0.70) {
        return {
          label: 'Review Suggested',
          dot: 'bg-amber-500',
          bg: 'bg-amber-950 border-amber-800',
          text: 'text-amber-400',
        };
      }
    }
    return {
      label: 'Low Similarity',
      dot: 'bg-amber-500',
      bg: 'bg-amber-950 border-amber-800',
      text: 'text-amber-400',
    };
  }
  return CONFIG[tier];
}

export function ConfidenceBadge({ tier, score }: Props) {
  const c = resolveConfig(tier, score);
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.dot}`} />
      {c.label}
      {tier === 'VECTOR' && score !== null && score !== undefined && (
        <span className="opacity-70">({(score * 100).toFixed(0)}%)</span>
      )}
    </span>
  );
}
