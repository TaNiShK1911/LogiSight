import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCharges, createCharge, addAlias, deleteAlias } from '../api/client';
import type { Charge } from '../api/types';

function AliasBadge({
  alias,
  chargeId,
  aliasId,
  onDelete,
}: {
  alias: string;
  chargeId: string;
  aliasId: number;
  onDelete: (chargeId: string, aliasId: string) => void;
}) {
  return (
    <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-outline-variant bg-surface-container-high text-label-sm text-on-surface-variant transition-colors hover:border-outline">
      {alias}
      <button
        onClick={() => onDelete(chargeId, aliasId)}
        className="text-outline-variant hover:text-error transition-colors flex items-center justify-center"
      >
        <span className="material-symbols-outlined text-[14px]">close</span>
      </button>
    </span>
  );
}

function ChargeRow({ charge, onAddAlias, onDeleteAlias }: {
  charge: Charge;
  onAddAlias: (chargeId: string, alias: string) => void;
  onDeleteAlias: (chargeId: string, aliasId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [newAlias, setNewAlias] = useState('');

  const handleAddAlias = () => {
    const trimmed = newAlias.trim();
    if (!trimmed) return;
    onAddAlias(charge.id, trimmed);
    setNewAlias('');
  };

  return (
    <div className="bg-surface-container-lowest rounded-2xl border border-surface-container overflow-hidden transition-all duration-300 hover:shadow-sm">
      <div
        className="flex flex-col sm:flex-row sm:items-center gap-4 px-6 py-5 cursor-pointer hover:bg-surface-container/50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-4 flex-1">
          <button className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${expanded ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'}`}>
            <span className={`material-symbols-outlined text-[20px] transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}>
              expand_more
            </span>
          </button>
          <div className="flex items-center gap-4">
            <span className="font-mono text-body-md font-bold text-apple-blue w-16 bg-apple-blue/10 px-2 py-1 rounded text-center">{charge.short_name}</span>
            <span className="font-body-md font-medium text-on-surface">{charge.name}</span>
          </div>
        </div>
        <div className="flex items-center gap-4 pl-12 sm:pl-0">
          <span className="flex items-center gap-1.5 text-label-sm text-on-surface-variant bg-surface-container-high px-3 py-1 rounded-full">
            <span className="material-symbols-outlined text-[16px]">sell</span>
            {charge.aliases?.length ?? 0} aliases
          </span>
          <span
            className={`px-3 py-1 rounded-full border text-label-sm font-medium flex items-center gap-1.5 ${
              charge.is_active
                ? 'bg-surface-container-highest text-on-surface border-transparent'
                : 'bg-surface-container text-on-surface-variant border-transparent'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${charge.is_active ? 'bg-apple-blue' : 'bg-outline-variant'}`}></span>
            {charge.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>
      
      <div className={`grid transition-all duration-300 ease-in-out ${expanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
        <div className="overflow-hidden">
          <div className="px-6 pb-6 pt-4 border-t border-surface-container bg-surface/50">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-[18px] text-primary">dictionary</span>
              <span className="font-label-sm text-label-sm font-semibold text-primary uppercase tracking-wider">Aliases (Tier 1 Dictionary)</span>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-6 min-h-[32px]">
              {charge.aliases?.length === 0 ? (
                <span className="text-body-md text-on-surface-variant italic py-1">No aliases configured yet. Add terms used by forwarders below.</span>
              ) : (
                charge.aliases?.map((a) => (
                  <AliasBadge
                    key={a.id}
                    alias={a.alias}
                    chargeId={charge.id}
                    aliasId={a.id}
                    onDelete={onDeleteAlias}
                  />
                ))
              )}
            </div>
            
            <div className="flex flex-col sm:flex-row gap-3 max-w-2xl">
              <div className="relative flex-1">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">add_label</span>
                <input
                  value={newAlias}
                  onChange={(e) => setNewAlias(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddAlias()}
                  className="w-full pl-11 pr-4 py-3 rounded-xl border border-outline-variant bg-surface text-on-surface placeholder:text-on-surface-variant/70 text-body-md focus:outline-none focus:border-primary transition-colors"
                  placeholder="Add alias... (e.g. Fuel Levy, Bunker Fee)"
                />
              </div>
              <button
                onClick={handleAddAlias}
                disabled={!newAlias.trim()}
                className="px-6 py-3 rounded-xl bg-primary hover:bg-on-surface disabled:opacity-50 text-on-primary font-label-sm text-label-sm transition-colors flex items-center justify-center gap-2 sm:w-auto w-full"
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
                Add Alias
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ChargeMaster() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newShortName, setNewShortName] = useState('');
  const [formError, setFormError] = useState('');

  const { data: charges = [], isLoading } = useQuery({
    queryKey: ['charges'],
    queryFn: getCharges,
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; short_name: string }) => createCharge(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['charges'] });
      setNewName('');
      setNewShortName('');
      setShowForm(false);
      setFormError('');
    },
    onError: (err: Error) => setFormError(err.message),
  });

  const aliasMutation = useMutation({
    mutationFn: ({ chargeId, alias }: { chargeId: string; alias: string }) =>
      addAlias(chargeId, alias),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['charges'] }),
  });

  const deleteAliasMutation = useMutation({
    mutationFn: ({ chargeId, aliasId }: { chargeId: string; aliasId: string }) =>
      deleteAlias(chargeId, aliasId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['charges'] }),
  });

  const handleCreate = () => {
    if (!newName.trim() || !newShortName.trim()) {
      setFormError('Both name and short name are required');
      return;
    }
    createMutation.mutate({ name: newName.trim(), short_name: newShortName.trim().toUpperCase() });
  };

  return (
    <div className="flex flex-col w-full relative">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-8">
          <div>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2">Settings</p>
            <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none">Charge Master</h1>
            <p className="text-on-surface-variant mt-3 text-body-md max-w-xl">
              Manage your internal charge standard and tier-1 alias dictionary. Never exposed to forwarders.
            </p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-label-sm text-label-sm transition-all shadow-sm hover:shadow-md transform active:scale-95"
          >
            <span className="material-symbols-outlined text-[18px]">{showForm ? 'close' : 'add'}</span>
            {showForm ? 'Cancel' : 'New Charge'}
          </button>
        </div>

        <div className="bg-primary/5 border border-primary/10 p-5 rounded-2xl flex items-start gap-4 mb-10">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="material-symbols-outlined text-primary text-[20px]">lightbulb</span>
          </div>
          <div>
            <h3 className="font-label-sm text-label-sm font-semibold text-primary mb-1">Alias Dictionary Tips</h3>
            <p className="text-body-md text-on-surface-variant">
              Aliases act as your Tier 1 synonym dictionary. Add known forwarder terms here (e.g. "Fuel Levy" for BAF) to ensure deterministic, instant mapping for all future quotes and invoices.
            </p>
          </div>
        </div>

        {showForm && (
          <div className="mb-10 bg-surface-container-lowest p-8 rounded-3xl shadow-sm border border-surface-container">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-surface-container-low flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-[20px]">playlist_add</span>
              </div>
              <h2 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">New Charge Entry</h2>
            </div>
            
            {formError && (
              <div className="flex items-center gap-2 p-4 rounded-xl bg-error-container text-on-error-container mb-6 border border-error/20">
                <span className="material-symbols-outlined text-[20px] text-error flex-shrink-0">error</span>
                <p className="text-body-md text-error">{formError}</p>
              </div>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="md:col-span-2">
                <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Full Charge Name</label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">badge</span>
                  <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-xl border border-outline-variant bg-surface text-on-surface placeholder:text-on-surface-variant/70 text-body-md focus:outline-none focus:border-primary transition-colors"
                    placeholder="e.g. Bunker Adjustment Factor"
                  />
                </div>
              </div>
              <div>
                <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Short Code</label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">short_text</span>
                  <input
                    value={newShortName}
                    onChange={(e) => setNewShortName(e.target.value.toUpperCase())}
                    className="w-full pl-11 pr-4 py-3 rounded-xl border border-outline-variant bg-surface text-on-surface font-mono uppercase placeholder:text-on-surface-variant/70 text-body-md focus:outline-none focus:border-primary transition-colors"
                    placeholder="BAF"
                    maxLength={10}
                  />
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 pt-6 border-t border-surface-container">
              <button
                onClick={() => { setShowForm(false); setNewName(''); setNewShortName(''); setFormError(''); }}
                className="px-6 py-3 rounded-full border border-outline-variant text-on-surface font-label-sm text-label-sm hover:bg-surface-container transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="px-8 py-3 rounded-full bg-primary hover:bg-on-surface disabled:opacity-60 text-on-primary font-label-sm text-label-sm shadow-sm transition-colors flex items-center justify-center gap-2"
              >
                {createMutation.isPending ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Charge'
                )}
              </button>
            </div>
          </div>
        )}

        <div className="space-y-4 pb-spacing-section-gap-lg">
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 rounded-2xl bg-surface-container-lowest border border-surface-container animate-pulse" />
              ))}
            </div>
          ) : charges.length === 0 ? (
            <div className="py-24 text-center bg-surface-container-lowest rounded-3xl border border-surface-container">
              <div className="w-20 h-20 bg-surface-container rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="material-symbols-outlined text-[40px] text-on-surface-variant">library_books</span>
              </div>
              <h3 className="font-headline-md-mobile text-[24px] text-on-surface tracking-tight mb-2">Your Charge Master is empty</h3>
              <p className="text-body-md text-on-surface-variant mb-8 max-w-md mx-auto">
                Start building your internal charge standard by adding your first charge entry.
              </p>
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-2 bg-primary text-on-primary px-8 py-3 rounded-full font-label-sm text-label-sm transition-colors hover:bg-on-surface"
              >
                <span className="material-symbols-outlined text-[18px]">add</span> Add First Charge
              </button>
            </div>
          ) : (
            charges.map((charge: Charge) => (
              <ChargeRow
                key={charge.id}
                charge={charge}
                onAddAlias={(chargeId, alias) => aliasMutation.mutate({ chargeId, alias })}
                onDeleteAlias={(chargeId, aliasId) => deleteAliasMutation.mutate({ chargeId, aliasId })}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
