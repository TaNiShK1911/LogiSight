import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
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
    <div className="p-6 rounded-3xl border border-surface-container bg-surface-container-lowest flex items-start justify-between gap-4 transition-all duration-200 hover:shadow-sm">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-surface flex items-center justify-center flex-shrink-0">
           <span className="material-symbols-outlined text-[24px] text-primary">domain</span>
        </div>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h3 className="font-display-sm text-[18px] font-semibold text-primary">{company.name}</h3>
            <span className="px-2 py-0.5 rounded text-label-sm font-mono tracking-wider bg-surface-container text-on-surface-variant font-medium">
              {company.short_name}
            </span>
          </div>
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className={`px-3 py-1 rounded-full font-label-sm text-[11px] uppercase tracking-wider font-bold ${
                company.type === 'client'
                  ? 'bg-emerald-500/10 text-emerald-600'
                  : 'bg-primary/10 text-primary'
              }`}
            >
              {company.type === 'client' ? 'Client' : 'Forwarder'}
            </span>
            <span
              className={`px-3 py-1 rounded-full font-label-sm text-[11px] uppercase tracking-wider font-bold ${
                company.is_active
                  ? 'bg-emerald-500/10 text-emerald-600'
                  : 'bg-surface-container text-outline-variant'
              }`}
            >
              {company.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          {(company.city || company.country) && (
            <p className="font-body-sm text-[13px] text-on-surface-variant flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">location_on</span>
              {[company.city, company.country].filter(Boolean).join(', ')}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={() => onToggle(company.id, !company.is_active)}
        disabled={toggling}
        className="flex-shrink-0 transition-transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
        title={company.is_active ? 'Deactivate' : 'Activate'}
      >
        {company.is_active ? (
          <span className="material-symbols-outlined text-[32px] text-emerald-500 !font-light">toggle_on</span>
        ) : (
          <span className="material-symbols-outlined text-[32px] text-outline-variant !font-light">toggle_off</span>
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
    <div className="flex flex-col w-full px-spacing-margin-desktop py-spacing-margin-desktop relative pb-10">
      <div className="flex items-end justify-between mb-8 max-w-5xl">
        <div>
           <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2 flex items-center gap-2">
             <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span> Platform Administration
           </p>
           <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none mb-3">Companies</h1>
           <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">Manage all platform companies and their admin users.</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary"
        >
          <span className="material-symbols-outlined text-[20px]">add</span> Create Company
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-container-highest/80 backdrop-blur-md">
          <div className="w-full max-w-2xl rounded-[32px] border border-surface-container bg-surface-container-lowest shadow-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-8 pb-6 border-b border-surface-container">
              <div>
                 <h2 className="font-headline-md text-headline-md text-primary font-semibold mb-1">Create Company</h2>
                 <p className="font-body-sm text-body-sm text-on-surface-variant">Onboard a new client or forwarder</p>
              </div>
              <button onClick={() => { setShowForm(false); reset(); setApiError(null); }} className="w-10 h-10 rounded-full flex items-center justify-center bg-surface hover:bg-surface-container transition-colors text-on-surface-variant">
                 <span className="material-symbols-outlined text-[24px]">close</span>
              </button>
            </div>
            <form
              onSubmit={handleSubmit((d) => createMutation.mutate(d))}
              className="p-8 space-y-6 max-h-[75vh] overflow-y-auto"
            >
              {apiError && (
                <div className="flex items-start gap-3 p-4 rounded-xl bg-error-container text-on-error-container">
                  <span className="material-symbols-outlined text-[20px] mt-0.5">error</span>
                  <p className="font-body-md text-body-md">{apiError}</p>
                </div>
              )}

              <div>
                 <p className="font-label-sm text-[12px] font-bold text-primary uppercase tracking-widest mb-4 flex items-center gap-2 border-b border-surface pb-2">
                    <span className="material-symbols-outlined text-[16px]">business</span> Company Details
                 </p>
                 <div className="grid grid-cols-2 gap-5">
                   <div className="flex flex-col gap-1.5">
                     <label className="font-label-sm text-label-sm font-semibold text-on-surface">Company Name</label>
                     <input {...register('name')} className="input-field" placeholder="Acme Imports Ltd" />
                     {errors.name && <p className="font-label-sm text-[12px] text-error">{errors.name.message}</p>}
                   </div>
                   <div className="flex flex-col gap-1.5">
                     <label className="font-label-sm text-label-sm font-semibold text-on-surface">Short Name</label>
                     <input {...register('short_name')} className="input-field" placeholder="ACME" />
                     {errors.short_name && <p className="font-label-sm text-[12px] text-error">{errors.short_name.message}</p>}
                   </div>
                 </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-label-sm text-label-sm font-semibold text-on-surface">Type</label>
                <div className="relative">
                   <select {...register('type')} className="input-field appearance-none w-full">
                     <option value="client">Client (Buyer/Importer)</option>
                     <option value="forwarder">Forwarder (Carrier)</option>
                   </select>
                   <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-outline-variant pointer-events-none">expand_more</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-5">
                <div className="flex flex-col gap-1.5">
                  <label className="font-label-sm text-label-sm font-semibold text-on-surface">City</label>
                  <input {...register('city')} className="input-field" placeholder="Singapore" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="font-label-sm text-label-sm font-semibold text-on-surface">Country</label>
                  <input {...register('country')} className="input-field" placeholder="Singapore" />
                </div>
              </div>

              <div className="pt-2">
                 <p className="font-label-sm text-[12px] font-bold text-primary uppercase tracking-widest mb-4 flex items-center gap-2 border-b border-surface pb-2">
                    <span className="material-symbols-outlined text-[16px]">person_add</span> First Admin User
                 </p>
                 <div className="grid grid-cols-2 gap-5">
                   <div className="flex flex-col gap-1.5">
                     <label className="font-label-sm text-label-sm font-semibold text-on-surface">Name</label>
                     <input {...register('admin_name')} className="input-field" placeholder="Jane Smith" />
                     {errors.admin_name && <p className="font-label-sm text-[12px] text-error">{errors.admin_name.message}</p>}
                   </div>
                   <div className="flex flex-col gap-1.5">
                     <label className="font-label-sm text-label-sm font-semibold text-on-surface">Email</label>
                     <input {...register('admin_email')} type="email" className="input-field" placeholder="jane@acme.com" />
                     {errors.admin_email && <p className="font-label-sm text-[12px] text-error">{errors.admin_email.message}</p>}
                   </div>
                 </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-label-sm text-label-sm font-semibold text-on-surface">Temporary Password</label>
                <input {...register('admin_password')} type="password" className="input-field" placeholder="Min. 8 characters" />
                {errors.admin_password && <p className="font-label-sm text-[12px] text-error">{errors.admin_password.message}</p>}
              </div>

              <div className="flex gap-4 pt-4 border-t border-surface-container">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); reset(); setApiError(null); }}
                  className="flex-1 btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1 btn-primary"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Company'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4 max-w-5xl">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-3xl bg-surface-container-lowest border border-surface-container animate-pulse shadow-sm" />
          ))}
        </div>
      ) : (
        <div className="space-y-10 max-w-5xl">
          {clients.length > 0 && (
            <div>
              <h2 className="font-label-sm text-[12px] font-bold text-outline-variant uppercase tracking-widest mb-4 ml-2">
                Clients ({clients.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
              <h2 className="font-label-sm text-[12px] font-bold text-outline-variant uppercase tracking-widest mb-4 ml-2">
                Forwarders ({forwarders.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <div className="py-24 flex flex-col items-center justify-center bg-surface-container-lowest rounded-3xl border border-surface-container border-dashed">
               <div className="w-20 h-20 bg-surface rounded-full flex items-center justify-center mb-6">
                  <span className="material-symbols-outlined text-[40px] text-outline-variant">domain_disabled</span>
               </div>
               <h2 className="font-headline-md-mobile text-[24px] font-semibold text-on-surface mb-2">No companies found</h2>
               <p className="font-body-md text-body-md text-on-surface-variant max-w-md text-center">
                  Get started by creating your first client or forwarder company on the platform.
               </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
