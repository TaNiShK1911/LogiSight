import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  AlertTriangle,
  Upload,
  CheckCircle2,
  Plus,
  ArrowRight,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { getQuotes, getInvoices } from '../api/client';
import type { QuoteHeader } from '../api/types';

const STATUS_CONFIG = {
  SUBMITTED: { label: 'Submitted', cls: 'bg-sky-900/60 text-sky-300 border-sky-800' },
  ACCEPTED: { label: 'Accepted', cls: 'bg-emerald-900/60 text-emerald-300 border-emerald-800' },
  REJECTED: { label: 'Rejected', cls: 'bg-red-900/60 text-red-300 border-red-800' },
};

function StatCard({
  label,
  value,
  Icon,
  color,
  border,
  bg,
}: {
  label: string;
  value: number | string;
  Icon: React.ElementType;
  color: string;
  border: string;
  bg: string;
}) {
  return (
    <div className={`p-5 rounded-xl border ${border} ${bg}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-slate-400">{label}</span>
        <div className={`w-8 h-8 rounded-lg bg-slate-900 border ${border} flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
      </div>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function QuoteRow({ quote }: { quote: QuoteHeader }) {
  const navigate = useNavigate();
  const sc = STATUS_CONFIG[quote.status];
  return (
    <tr
      className="border-b border-slate-800/60 hover:bg-slate-800/30 cursor-pointer transition-colors"
      onClick={() => navigate(`/app/quotes/${quote.id}`)}
    >
      <td className="px-4 py-3 font-mono text-sm text-sky-400">{quote.quote_ref}</td>
      <td className="px-4 py-3 text-sm text-slate-300">
        {quote.forwarder?.name ?? quote.buyer?.name ?? '—'}
      </td>
      <td className="px-4 py-3">
        <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${sc.cls}`}>
          {sc.label}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(quote.created_at).toLocaleDateString()}
      </td>
      <td className="px-4 py-3 text-right">
        <ArrowRight className="w-4 h-4 text-slate-600 inline" />
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
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Platform Overview</h1>
          <p className="text-slate-400 mt-1">Super Admin dashboard</p>
        </div>
        <div className="grid md:grid-cols-2 gap-5">
          <div
            onClick={() => navigate('/app/companies')}
            className="p-6 rounded-xl border border-slate-700 bg-slate-900/40 hover:border-slate-600 cursor-pointer transition-colors group"
          >
            <FileText className="w-8 h-8 text-slate-400 group-hover:text-sky-400 mb-3 transition-colors" />
            <h2 className="text-lg font-semibold text-slate-100 mb-1">Manage Companies</h2>
            <p className="text-sm text-slate-400">Create and manage client and forwarder companies.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            Welcome back{user?.name ? `, ${user.name.split(' ')[0]}` : ''}
          </h1>
          <p className="text-slate-400 mt-1">{user?.company_name}</p>
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

      {(quotesLoading || invoicesLoading) ? (
        <div className="grid md:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-5">
          {isClient ? (
            <>
              <StatCard
                label="Open Quotes"
                value={openQuotes}
                Icon={Clock}
                color="text-sky-400"
                border="border-sky-800"
                bg="bg-sky-950/20"
              />
              <StatCard
                label="Invoices This Month"
                value={invoicesThisMonth}
                Icon={Upload}
                color="text-emerald-400"
                border="border-emerald-800"
                bg="bg-emerald-950/20"
              />
              <StatCard
                label="Accepted Quotes"
                value={acceptedQuotes}
                Icon={CheckCircle2}
                color="text-amber-400"
                border="border-amber-800"
                bg="bg-amber-950/20"
              />
            </>
          ) : (
            <>
              <StatCard
                label="My Quotes"
                value={quotes.length}
                Icon={FileText}
                color="text-sky-400"
                border="border-sky-800"
                bg="bg-sky-950/20"
              />
              <StatCard
                label="Accepted"
                value={acceptedQuotes}
                Icon={CheckCircle2}
                color="text-emerald-400"
                border="border-emerald-800"
                bg="bg-emerald-950/20"
              />
              <StatCard
                label="Invoices Uploaded"
                value={invoices.length}
                Icon={Upload}
                color="text-amber-400"
                border="border-amber-800"
                bg="bg-amber-950/20"
              />
            </>
          )}
        </div>
      )}

      {isClient && openQuotes > 0 && (
        <div className="flex items-center gap-3 p-4 rounded-lg border border-amber-800 bg-amber-950/20">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <p className="text-sm text-amber-300">
            <span className="font-semibold">{openQuotes} quote{openQuotes > 1 ? 's' : ''}</span> awaiting your review.
          </p>
          <button
            onClick={() => navigate('/app/quotes')}
            className="ml-auto text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors"
          >
            Review <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {isForwarder && (
        <div
          onClick={() => navigate('/app/quotes/new')}
          className="p-6 rounded-xl border border-dashed border-slate-700 hover:border-sky-700 cursor-pointer transition-colors group text-center"
        >
          <Plus className="w-8 h-8 text-slate-600 group-hover:text-sky-400 mx-auto mb-2 transition-colors" />
          <p className="text-sm font-medium text-slate-400 group-hover:text-sky-300 transition-colors">
            Submit a new freight quote
          </p>
        </div>
      )}

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-slate-500" /> Recent Quotes
          </h2>
          <button
            onClick={() => navigate('/app/quotes')}
            className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 transition-colors"
          >
            View all <ArrowRight className="w-3 h-3" />
          </button>
        </div>
        {recentQuotes.length === 0 ? (
          <div className="py-12 text-center text-slate-600 text-sm">No quotes yet.</div>
        ) : (
          <div className="rounded-xl border border-slate-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400">Ref</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400">
                    {isClient ? 'Forwarder' : 'Client'}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400">Date</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {recentQuotes.map((q) => (
                  <QuoteRow key={q.id} quote={q} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
