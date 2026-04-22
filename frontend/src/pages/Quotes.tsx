import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, ArrowRight, FileText } from 'lucide-react';
import { getQuotes } from '../api/client';
import { useAuth } from '../hooks/useAuth';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Submitted', cls: 'bg-sky-900/60 text-sky-300 border-sky-800' },
  ACCEPTED: { label: 'Accepted', cls: 'bg-emerald-900/60 text-emerald-300 border-emerald-800' },
  REJECTED: { label: 'Rejected', cls: 'bg-red-900/60 text-red-300 border-red-800' },
};

export function Quotes() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isClient = user?.role === 'client';
  const isForwarder = user?.role === 'forwarder';

  const { data: quotes = [], isLoading } = useQuery({
    queryKey: ['quotes'],
    queryFn: getQuotes,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Quotes</h1>
          <p className="text-slate-400 mt-1 text-sm">
            {isClient
              ? 'Review and act on incoming freight quotes'
              : 'Track your submitted freight quotes'}
          </p>
        </div>
        {isForwarder && (
          <button
            onClick={() => navigate('/app/quotes/new')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-sm font-semibold transition-colors"
          >
            <Plus className="w-4 h-4" /> New Quote
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-lg border border-slate-800 bg-slate-900/40 animate-pulse" />
          ))}
        </div>
      ) : quotes.length === 0 ? (
        <div className="py-24 text-center">
          <FileText className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-400 font-medium">No quotes yet</p>
          {isForwarder && (
            <button
              onClick={() => navigate('/app/quotes/new')}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-sm font-semibold transition-colors"
            >
              <Plus className="w-4 h-4" /> Submit your first quote
            </button>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60">
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Quote Ref</th>
                {isClient && (
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Forwarder</th>
                )}
                {isForwarder && (
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Client</th>
                )}
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Route</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">AWB</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Status</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Date</th>
                {isForwarder && (
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Note</th>
                )}
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => {
                const sc = STATUS_CONFIG[q.status];
                return (
                  <tr
                    key={q.id}
                    className="border-b border-slate-800/60 hover:bg-slate-800/30 cursor-pointer transition-colors"
                    onClick={() => navigate(`/app/quotes/${q.id}`)}
                  >
                    <td className="px-5 py-3.5 font-mono text-sky-400 font-medium">{q.quote_ref}</td>
                    {isClient && (
                      <td className="px-5 py-3.5 text-slate-300">{q.forwarder?.name ?? '—'}</td>
                    )}
                    {isForwarder && (
                      <td className="px-5 py-3.5 text-slate-300">{q.buyer?.name ?? '—'}</td>
                    )}
                    <td className="px-5 py-3.5 text-slate-400">
                      {q.origin_airport?.iata_code} → {q.destination_airport?.iata_code}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-400">{q.tracking_number}</td>
                    <td className="px-5 py-3.5">
                      <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${sc.cls}`}>
                        {sc.label}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500">
                      {new Date(q.created_at).toLocaleDateString()}
                    </td>
                    {isForwarder && (
                      <td className="px-5 py-3.5 text-xs text-slate-500 max-w-[180px] truncate">
                        {q.rejection_note ?? '—'}
                      </td>
                    )}
                    <td className="px-5 py-3.5 text-right">
                      <ArrowRight className="w-4 h-4 text-slate-600 inline" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
