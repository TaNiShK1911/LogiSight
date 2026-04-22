import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, ChevronDown, ChevronRight, X, BookOpen, Tag } from 'lucide-react';
import { getCharges, createCharge, addAlias, deleteAlias } from '../api/client';
import type { Charge } from '../api/types';

function AliasBadge({
  alias,
  chargeId,
  aliasId,
  onDelete,
}: {
  alias: string;
  chargeId: number;
  aliasId: number;
  onDelete: (chargeId: number, aliasId: number) => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-slate-700 bg-slate-800 text-xs text-slate-400">
      {alias}
      <button
        onClick={() => onDelete(chargeId, aliasId)}
        className="text-slate-600 hover:text-red-400 transition-colors ml-0.5"
      >
        <X className="w-3 h-3" />
      </button>
    </span>
  );
}

function ChargeRow({ charge, onAddAlias, onDeleteAlias }: {
  charge: Charge;
  onAddAlias: (chargeId: number, alias: string) => void;
  onDeleteAlias: (chargeId: number, aliasId: number) => void;
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
    <div className="border border-slate-800 rounded-xl overflow-hidden">
      <div
        className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-slate-800/30 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-slate-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
        )}
        <div className="flex-1 flex items-center gap-3">
          <span className="font-mono text-sm font-bold text-sky-400 w-14 flex-shrink-0">{charge.short_name}</span>
          <span className="font-medium text-slate-100">{charge.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{charge.aliases?.length ?? 0} aliases</span>
          <span
            className={`px-2 py-0.5 rounded-full border text-xs font-medium ${
              charge.is_active
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            {charge.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>
      {expanded && (
        <div className="px-5 pb-5 pt-2 border-t border-slate-800 bg-slate-900/30">
          <div className="flex items-center gap-2 mb-3">
            <Tag className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Aliases (Tier 1 dictionary)</span>
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {charge.aliases?.length === 0 ? (
              <span className="text-xs text-slate-600 italic">No aliases yet</span>
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
          <div className="flex gap-2">
            <input
              value={newAlias}
              onChange={(e) => setNewAlias(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddAlias()}
              className="flex-1 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
              placeholder="Add alias… (e.g. Fuel Levy, Bunker Fee)"
            />
            <button
              onClick={handleAddAlias}
              disabled={!newAlias.trim()}
              className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
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
    mutationFn: ({ chargeId, alias }: { chargeId: number; alias: string }) =>
      addAlias(chargeId, alias),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['charges'] }),
  });

  const deleteAliasMutation = useMutation({
    mutationFn: ({ chargeId, aliasId }: { chargeId: number; aliasId: number }) =>
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Charge Master</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Your internal charge standard — never exposed to forwarders
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-sm font-semibold transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Charge
        </button>
      </div>

      <div className="p-4 rounded-lg border border-sky-800/50 bg-sky-950/20 flex gap-3">
        <BookOpen className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-sky-300">
          Aliases act as your Tier 1 synonym dictionary. Add known forwarder terms here to ensure deterministic, instant mapping for all future quotes and invoices.
        </p>
      </div>

      {showForm && (
        <div className="p-5 rounded-xl border border-slate-700 bg-slate-900/60 space-y-4">
          <h2 className="text-sm font-semibold text-slate-300">New Charge Entry</h2>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Full Name</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="input-field"
                placeholder="e.g. Bunker Adjustment Factor"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Short Code</label>
              <input
                value={newShortName}
                onChange={(e) => setNewShortName(e.target.value.toUpperCase())}
                className="input-field font-mono"
                placeholder="BAF"
                maxLength={10}
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => { setShowForm(false); setNewName(''); setNewShortName(''); setFormError(''); }}
              className="px-4 py-2 rounded-lg border border-slate-700 text-slate-300 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
            >
              {createMutation.isPending ? 'Creating…' : 'Create Charge'}
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-14 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
          ))}
        </div>
      ) : charges.length === 0 ? (
        <div className="py-16 text-center">
          <BookOpen className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-400 font-medium">Your Charge Master is empty</p>
          <p className="text-sm text-slate-600 mt-1">Add your first charge entry above</p>
        </div>
      ) : (
        <div className="space-y-3">
          {charges.map((charge: Charge) => (
            <ChargeRow
              key={charge.id}
              charge={charge}
              onAddAlias={(chargeId, alias) => aliasMutation.mutate({ chargeId, alias })}
              onDeleteAlias={(chargeId, aliasId) => deleteAliasMutation.mutate({ chargeId, aliasId })}
            />
          ))}
        </div>
      )}
    </div>
  );
}
