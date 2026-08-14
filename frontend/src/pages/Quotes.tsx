import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getQuotes } from '../api/client';
import { useAuth } from '../hooks/useAuth';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Submitted', cls: 'bg-surface-container-high text-on-surface' },
  ACCEPTED: { label: 'Accepted', cls: 'bg-surface-container text-on-surface-variant' },
  REJECTED: { label: 'Rejected', cls: 'bg-error-container text-on-error-container' },
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
    <div className="flex flex-col w-full relative">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop mb-spacing-section-gap-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-10">
          <div>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2">Commerce</p>
            <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none">Quotes</h1>
            <p className="text-on-surface-variant mt-2 text-body-md max-w-xl">
              {isClient
                ? 'Review and act on incoming freight quotes.'
                : 'Track your submitted freight quotes.'}
            </p>
          </div>
          {isForwarder && (
            <button
              onClick={() => navigate('/app/quotes/new')}
              className="flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-label-sm text-label-sm transition-all shadow-sm hover:shadow-md transform active:scale-95"
            >
              <span className="material-symbols-outlined text-[18px]">add</span> New Quote
            </button>
          )}
        </div>

        <div className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">Active Quotes</h3>
              <p className="font-body-md text-body-md text-on-surface-variant mt-1">All submitted and processed quotes.</p>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-16 rounded-xl border border-surface-container-highest bg-surface-container-highest/40 animate-pulse" />
              ))}
            </div>
          ) : quotes.length === 0 ? (
            <div className="py-24 text-center">
              <span className="material-symbols-outlined text-[48px] text-outline-variant mx-auto mb-4">request_quote</span>
              <p className="text-on-surface-variant font-body-md mb-6">No quotes yet</p>
              {isForwarder && (
                <button
                  onClick={() => navigate('/app/quotes/new')}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-apple-blue hover:bg-[#005bb5] text-white font-label-sm text-label-sm shadow-sm transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">add</span> Submit your first quote
                </button>
              )}
            </div>
          ) : (
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-surface-container-highest">
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Quote Ref</th>
                    {isClient && (
                      <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Forwarder</th>
                    )}
                    {isForwarder && (
                      <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Client</th>
                    )}
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Route</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">AWB</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Status</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Date</th>
                    {isForwarder && (
                      <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Note</th>
                    )}
                    <th className="py-4 px-4"></th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-body-md">
                  {quotes.map((q) => {
                    const sc = STATUS_CONFIG[q.status];
                    return (
                      <tr
                        key={q.id}
                        className="border-b border-surface-container hover:bg-surface-container/30 transition-colors group cursor-pointer"
                        onClick={() => navigate(`/app/quotes/${q.id}`)}
                      >
                        <td className="py-4 px-4 font-mono text-apple-blue font-medium text-sm">{q.quote_ref}</td>
                        {isClient && (
                          <td className="py-4 px-4 text-on-surface">{q.forwarder?.name ?? '—'}</td>
                        )}
                        {isForwarder && (
                          <td className="py-4 px-4 text-on-surface">{q.buyer?.name ?? '—'}</td>
                        )}
                        <td className="py-4 px-4 text-on-surface-variant text-sm">
                          {q.origin_airport?.iata_code} → {q.destination_airport?.iata_code}
                        </td>
                        <td className="py-4 px-4 font-mono text-sm text-on-surface-variant">{q.tracking_number}</td>
                        <td className="py-4 px-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-label-sm text-label-sm ${sc.cls}`}>
                            {sc.label}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-outline-variant text-sm">
                          {new Date(q.created_at).toLocaleDateString()}
                        </td>
                        {isForwarder && (
                          <td className="py-4 px-4 text-outline-variant text-sm max-w-[180px] truncate">
                            {q.rejection_note ?? '—'}
                          </td>
                        )}
                        <td className="py-4 px-4 text-right">
                          <button className="text-on-surface-variant hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                            <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
