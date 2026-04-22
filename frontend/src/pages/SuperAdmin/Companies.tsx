import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Building2, Plus, ToggleLeft, ToggleRight, X, AlertCircle } from 'lucide-react';
import { getCompanies, createCompany, updateCompanyStatus } from '../../api/client';
import type { Company } from '../../api/types';

const schema = z.object({
  name: z.string().min(2, 'Company name required'),
  short_name: z.string().min(1, 'Short name required').max(10),
  type: z.enum(['client', 'forwarder']),
  city: z.string().optional(),
  country: z.string().optional(),
  admin_name: z.string().min(2, 'Admin name required'),
  admin_email: z.string().email('Valid email required'),
  admin_password: z.string().min(8, 'At least 8 characters'),
});

type FormData = z.infer<typeof schema>;

function CompanyCard({
  company,
  onToggle,
  toggling,
}: {
  company: Company;
  onToggle: (id: number, active: boolean) => void;
  toggling: boolean;
}) {
  return (
    <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 flex items-start justify-between gap-4">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-5 h-5 text-slate-400" />
        </div>
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="font-semibold text-slate-100">{company.name}</h3>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono border border-slate-700 text-slate-500">
              {company.short_name}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded-full border text-xs font-medium ${
                company.type === 'client'
                  ? 'bg-emerald-950/50 text-emerald-400 border-emerald-800'
                  : 'bg-sky-950/50 text-sky-400 border-sky-800'
              }`}
            >
              {company.type === 'client' ? 'Client' : 'Forwarder'}
            </span>
            <span
              className={`px-2 py-0.5 rounded-full border text-xs font-medium ${
                company.is_active
                  ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800'
                  : 'bg-slate-800 text-slate-500 border-slate-700'
              }`}
            >
              {company.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          {(company.city || company.country) && (
            <p className="text-xs text-slate-500 mt-1">
              {[company.city, company.country].filter(Boolean).join(', ')}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={() => onToggle(company.id, !company.is_active)}
        disabled={toggling}
        className="flex-shrink-0 text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-40"
        title={company.is_active ? 'Deactivate' : 'Activate'}
      >
        {company.is_active ? (
          <ToggleRight className="w-7 h-7 text-emerald-400" />
        ) : (
          <ToggleLeft className="w-7 h-7" />
        )}
      </button>
    </div>
  );
}

export function Companies() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: getCompanies,
  });

  const createMutation = useMutation({
    mutationFn: createCompany,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] });
      setShowForm(false);
      reset();
      setApiError(null);
    },
    onError: (err: Error) => setApiError(err.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      updateCompanyStatus(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { type: 'client' } });

  const clients = companies.filter((c) => c.type === 'client');
  const forwarders = companies.filter((c) => c.type === 'forwarder');

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Companies</h1>
          <p className="text-slate-400 mt-1">Manage all platform companies and their admin users</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-sm font-semibold transition-colors"
        >
          <Plus className="w-4 h-4" /> Create Company
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-slate-800">
              <h2 className="text-lg font-semibold text-slate-100">Create Company</h2>
              <button onClick={() => { setShowForm(false); reset(); setApiError(null); }} className="text-slate-500 hover:text-slate-300">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form
              onSubmit={handleSubmit((d) => createMutation.mutate(d))}
              className="p-6 space-y-4 max-h-[75vh] overflow-y-auto"
            >
              {apiError && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-red-950/60 border border-red-800">
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-300">{apiError}</p>
                </div>
              )}

              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Company Details</p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Company Name</label>
                  <input {...register('name')} className="input-field" placeholder="Acme Imports Ltd" />
                  {errors.name && <p className="err">{errors.name.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Short Name</label>
                  <input {...register('short_name')} className="input-field" placeholder="ACME" />
                  {errors.short_name && <p className="err">{errors.short_name.message}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Type</label>
                <select {...register('type')} className="input-field">
                  <option value="client">Client (Buyer/Importer)</option>
                  <option value="forwarder">Forwarder (Carrier)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">City</label>
                  <input {...register('city')} className="input-field" placeholder="Singapore" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Country</label>
                  <input {...register('country')} className="input-field" placeholder="Singapore" />
                </div>
              </div>

              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider pt-2">First Admin User</p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
                  <input {...register('admin_name')} className="input-field" placeholder="Jane Smith" />
                  {errors.admin_name && <p className="err">{errors.admin_name.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
                  <input {...register('admin_email')} type="email" className="input-field" placeholder="jane@acme.com" />
                  {errors.admin_email && <p className="err">{errors.admin_email.message}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Temporary Password</label>
                <input {...register('admin_password')} type="password" className="input-field" placeholder="Min. 8 characters" />
                {errors.admin_password && <p className="err">{errors.admin_password.message}</p>}
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); reset(); setApiError(null); }}
                  className="flex-1 py-2.5 rounded-lg border border-slate-700 text-slate-300 hover:text-slate-100 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1 py-2.5 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
                >
                  {createMutation.isPending ? 'Creating…' : 'Create Company'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          {clients.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                Clients ({clients.length})
              </h2>
              <div className="space-y-3">
                {clients.map((c) => (
                  <CompanyCard
                    key={c.id}
                    company={c}
                    onToggle={(id, active) => toggleMutation.mutate({ id, active })}
                    toggling={toggleMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}
          {forwarders.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                Forwarders ({forwarders.length})
              </h2>
              <div className="space-y-3">
                {forwarders.map((c) => (
                  <CompanyCard
                    key={c.id}
                    company={c}
                    onToggle={(id, active) => toggleMutation.mutate({ id, active })}
                    toggling={toggleMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}
          {companies.length === 0 && (
            <div className="py-16 text-center text-slate-600">
              No companies yet. Create the first one above.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
