import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getQuotes, getInvoices } from '../api/client';
import type { QuoteHeader } from '../api/types';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Submitted', cls: 'bg-surface-container-high text-on-surface' },
  ACCEPTED: { label: 'Accepted', cls: 'bg-surface-container text-on-surface-variant' },
  REJECTED: { label: 'Rejected', cls: 'bg-error-container text-on-error-container' },
};

function QuoteRow({ quote }: { quote: QuoteHeader }) {
  const navigate = useNavigate();
  const sc = STATUS_CONFIG[quote.status];
  return (
    <tr
      className="border-b border-surface-container hover:bg-surface-container/30 transition-colors group cursor-pointer"
      onClick={() => navigate(`/app/quotes/${quote.id}`)}
    >
      <td className="py-4 px-4 text-on-surface tabular-nums font-mono text-sm">{quote.quote_ref}</td>
      <td className="py-4 px-4 text-on-surface">
        {quote.forwarder?.name ?? quote.buyer?.name ?? '—'}
      </td>
      <td className="py-4 px-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-label-sm text-label-sm ${sc.cls}`}>
          {sc.label}
        </span>
      </td>
      <td className="py-4 px-4 text-on-surface-variant text-sm">
        {new Date(quote.created_at).toLocaleDateString()}
      </td>
      <td className="py-4 px-4 text-right">
        <button className="text-on-surface-variant hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
        </button>
      </td>
    </tr>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isClient = user?.role === 'client';
  const isForwarder = user?.role === 'forwarder';

  const { data: quotes = [], isLoading: quotesLoading } = useQuery({
    queryKey: ['quotes'],
    queryFn: getQuotes,
    enabled: isClient || isForwarder,
  });

  const { data: invoices = [], isLoading: invoicesLoading } = useQuery({
    queryKey: ['invoices'],
    queryFn: () => getInvoices(),
    enabled: isClient || isForwarder,
  });

  const openQuotes = quotes.filter((q) => q.status === 'SUBMITTED').length;
  const acceptedQuotes = quotes.filter((q) => q.status === 'ACCEPTED').length;
  const recentQuotes = [...quotes].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  ).slice(0, 5);

  const now = new Date();
  const invoicesThisMonth = invoices.filter((inv) => {
    const d = new Date(inv.uploaded_at ?? inv.invoice_date);
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  }).length;

  if (user?.role === 'super_admin') {
    return (
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop">
        <div className="mb-10">
          <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2">Overview</p>
          <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none">Super Admin</h1>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          <div
            onClick={() => navigate('/app/companies')}
            className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300 cursor-pointer"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full -mr-16 -mt-16 transition-transform duration-500 group-hover:scale-110"></div>
            <div className="flex justify-between items-start mb-12">
              <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-[24px]">corporate_fare</span>
              </div>
            </div>
            <div>
              <p className="font-body-md text-body-md text-on-surface-variant mb-1">Manage Companies</p>
              <h2 className="font-headline-md text-headline-md text-on-surface tracking-tight">View</h2>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full relative">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop mb-spacing-section-gap-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-10">
          <div>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2">Overview</p>
            <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none">Command Center</h1>
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

        {(quotesLoading || invoicesLoading) ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-surface-container-lowest h-[220px] rounded-2xl shadow-sm animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            {isClient ? (
              <>
                <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full -mr-16 -mt-16 transition-transform duration-500 group-hover:scale-110"></div>
                  <div className="flex justify-between items-start mb-12">
                    <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center">
                      <span className="material-symbols-outlined text-primary text-[24px]">pending_actions</span>
                    </div>
                  </div>
                  <div>
                    <p className="font-body-md text-body-md text-on-surface-variant mb-1">Open Quotes</p>
                    <div className="flex items-baseline gap-2">
                      <h2 className="font-headline-md text-headline-md text-on-surface tabular-nums tracking-tight">{openQuotes}</h2>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">Pending</span>
                    </div>
                  </div>
                </div>

                <div className="bg-primary p-8 rounded-2xl shadow-md relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-br from-transparent via-on-primary/5 to-transparent"></div>
                  <div className="absolute bottom-0 right-0 w-48 h-48 bg-on-primary/10 rounded-tl-full translate-x-12 translate-y-12 transition-transform duration-700 group-hover:scale-125"></div>
                  <div className="flex justify-between items-start mb-12 relative z-10">
                    <div className="w-12 h-12 rounded-xl bg-on-primary/20 flex items-center justify-center backdrop-blur-sm">
                      <span className="material-symbols-outlined text-on-primary text-[24px]">receipt_long</span>
                    </div>
                  </div>
                  <div className="relative z-10">
                    <p className="font-body-md text-body-md text-on-primary/80 mb-1">Invoices This Month</p>
                    <div className="flex items-baseline gap-2">
                      <h2 className="font-headline-md text-headline-md text-on-primary tabular-nums tracking-tight">{invoicesThisMonth}</h2>
                      <span className="font-label-sm text-label-sm text-on-primary/80">Processed</span>
                    </div>
                  </div>
                </div>

                <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
                  <div className="flex justify-between items-start mb-12">
                    <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center">
                      <span className="material-symbols-outlined text-primary text-[24px]">check_circle</span>
                    </div>
                  </div>
                  <div>
                    <p className="font-body-md text-body-md text-on-surface-variant mb-1">Accepted Quotes</p>
                    <div className="flex items-baseline gap-2">
                      <h2 className="font-headline-md text-headline-md text-on-surface tabular-nums tracking-tight">{acceptedQuotes}</h2>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">Total</span>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full -mr-16 -mt-16 transition-transform duration-500 group-hover:scale-110"></div>
                  <div className="flex justify-between items-start mb-12">
                    <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center">
                      <span className="material-symbols-outlined text-primary text-[24px]">description</span>
                    </div>
                  </div>
                  <div>
                    <p className="font-body-md text-body-md text-on-surface-variant mb-1">My Quotes</p>
                    <div className="flex items-baseline gap-2">
                      <h2 className="font-headline-md text-headline-md text-on-surface tabular-nums tracking-tight">{quotes.length}</h2>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">Submitted</span>
                    </div>
                  </div>
                </div>

                <div className="bg-primary p-8 rounded-2xl shadow-md relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-br from-transparent via-on-primary/5 to-transparent"></div>
                  <div className="absolute bottom-0 right-0 w-48 h-48 bg-on-primary/10 rounded-tl-full translate-x-12 translate-y-12 transition-transform duration-700 group-hover:scale-125"></div>
                  <div className="flex justify-between items-start mb-12 relative z-10">
                    <div className="w-12 h-12 rounded-xl bg-on-primary/20 flex items-center justify-center backdrop-blur-sm">
                      <span className="material-symbols-outlined text-on-primary text-[24px]">check_circle</span>
                    </div>
                  </div>
                  <div className="relative z-10">
                    <p className="font-body-md text-body-md text-on-primary/80 mb-1">Accepted</p>
                    <div className="flex items-baseline gap-2">
                      <h2 className="font-headline-md text-headline-md text-on-primary tabular-nums tracking-tight">{acceptedQuotes}</h2>
                      <span className="font-label-sm text-label-sm text-on-primary/80">Approved</span>
                    </div>
                  </div>
                </div>

                <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
                  <div className="flex justify-between items-start mb-12">
                    <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center">
                      <span className="material-symbols-outlined text-primary text-[24px]">upload_file</span>
                    </div>
                  </div>
                  <div>
                    <p className="font-body-md text-body-md text-on-surface-variant mb-1">Invoices Uploaded</p>
                    <div className="flex items-baseline gap-2">
                      <h2 className="font-headline-md text-headline-md text-on-surface tabular-nums tracking-tight">{invoices.length}</h2>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">Documents</span>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      <div className="px-spacing-margin-desktop pb-spacing-section-gap-lg">
        {isClient && openQuotes > 0 && (
          <div className="bg-error-container p-6 rounded-2xl flex items-center gap-4 mb-8">
            <span className="material-symbols-outlined text-on-error-container text-[24px]">warning</span>
            <p className="font-body-md text-body-md text-on-error-container flex-1">
              <span className="font-semibold">{openQuotes} quote{openQuotes > 1 ? 's' : ''}</span> awaiting your review.
            </p>
            <button
              onClick={() => navigate('/app/quotes')}
              className="font-label-sm text-label-sm text-on-error-container bg-error-container hover:bg-error/20 px-4 py-2 rounded-full transition-colors flex items-center gap-2"
            >
              Review <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>
        )}

        <div className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">Recent Quotes</h3>
              <p className="font-body-md text-body-md text-on-surface-variant mt-1">Latest freight quotes and their status.</p>
            </div>
            <button
              onClick={() => navigate('/app/quotes')}
              className="font-label-sm text-label-sm text-primary hover:text-on-surface-variant transition-colors flex items-center gap-1"
            >
              View All <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>

          <div className="w-full overflow-x-auto">
            {recentQuotes.length === 0 ? (
              <div className="py-12 text-center text-on-surface-variant font-body-md">No quotes yet.</div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-surface-container-highest">
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Ref</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">
                      {isClient ? 'Forwarder' : 'Client'}
                    </th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Status</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Date</th>
                    <th className="py-4 px-4"></th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-body-md">
                  {recentQuotes.map((q) => (
                    <QuoteRow key={q.id} quote={q} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
