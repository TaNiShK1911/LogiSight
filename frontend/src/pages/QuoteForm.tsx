import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getCompanies, getAirports, getCurrencies, submitQuote } from '../api/client';
import type { ChargeBasis, QuoteSubmitPayload } from '../api/types';

const BASIS_OPTIONS: ChargeBasis[] = ['Per KG', 'Per Shipment', 'Per CBM', 'Flat Rate', 'Per Chg Wt'];

interface ChargeLine {
  raw_charge_name: string;
  rate: string;
  basis: ChargeBasis;
  qty: string;
  amount: string;
}

const emptyCharge = (): ChargeLine => ({
  raw_charge_name: '',
  rate: '',
  basis: 'Per KG',
  qty: '1',
  amount: '',
});

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">{label}</label>
      {children}
      {error && <p className="mt-1.5 text-label-sm text-error ml-1 flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">error</span> {error}</p>}
    </div>
  );
}

export function QuoteForm() {
  const navigate = useNavigate();
  const [charges, setCharges] = useState<ChargeLine[]>([emptyCharge()]);
  const [header, setHeader] = useState({
    buyer_id: '',
    origin_airport_id: '',
    destination_airport_id: '',
    tracking_number: '',
    gross_weight: '',
    volumetric_weight: '',
    chargeable_weight: '',
    currency_id: '',
    etd: '',
    eta: '',
    goods_description: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const { data: companies = [] } = useQuery({ queryKey: ['companies'], queryFn: getCompanies });
  const { data: airports = [] } = useQuery({ queryKey: ['airports'], queryFn: getAirports });
  const { data: currencies = [] } = useQuery({ queryKey: ['currencies'], queryFn: getCurrencies });

  const clientCompanies = companies.filter((c) => c.type === 'client' && c.is_active);

  const submitMutation = useMutation({
    mutationFn: (payload: QuoteSubmitPayload) => submitQuote(payload),
    onSuccess: (data) => navigate(`/app/quotes/${data.id}`),
    onError: (err: Error) => setApiError(err.message),
  });

  // Auto-calculate chargeable weight when gross or volumetric changes
  useEffect(() => {
    const gross = parseFloat(header.gross_weight) || 0;
    const volumetric = parseFloat(header.volumetric_weight) || 0;
    const calculated = Math.max(gross, volumetric);
    if (calculated > 0 && calculated !== parseFloat(header.chargeable_weight)) {
      setHeader((p) => ({ ...p, chargeable_weight: calculated.toFixed(2) }));
    }
  }, [header.gross_weight, header.volumetric_weight]);

  const updateCharge = (idx: number, field: keyof ChargeLine, value: string) => {
    setCharges((prev) =>
      prev.map((c, i) => {
        if (i !== idx) return c;
        const updated = { ...c, [field]: value };

        // Auto-calculate amount if rate and qty are both provided
        if (field === 'rate' || field === 'qty') {
          const r = parseFloat(field === 'rate' ? value : updated.rate) || 0;
          const q = parseFloat(field === 'qty' ? value : updated.qty) || 0;
          // Only auto-calculate if both rate and qty have values
          if (r > 0 && q > 0) {
            updated.amount = (r * q).toFixed(2);
          }
        }

        return updated;
      }),
    );
  };

  const addCharge = () => setCharges((prev) => [...prev, emptyCharge()]);
  const removeCharge = (idx: number) => setCharges((prev) => prev.filter((_, i) => i !== idx));

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!header.buyer_id) errs.buyer_id = 'Select a client';
    if (!header.origin_airport_id) errs.origin = 'Select origin airport';
    if (!header.destination_airport_id) errs.destination = 'Select destination airport';
    if (!header.tracking_number.trim()) errs.tracking = 'AWB/tracking number required';
    if (!header.gross_weight || isNaN(Number(header.gross_weight))) errs.gross = 'Valid weight required';
    if (!header.currency_id) errs.currency = 'Select currency';
    charges.forEach((c, i) => {
      if (!c.raw_charge_name.trim()) errs[`charge_name_${i}`] = 'Charge name required';
      if (!c.amount || isNaN(Number(c.amount))) errs[`charge_amount_${i}`] = 'Amount required';
      // Rate and qty are now optional - only validate if provided
      if (c.rate && isNaN(Number(c.rate))) errs[`charge_rate_${i}`] = 'Invalid rate';
      if (c.qty && isNaN(Number(c.qty))) errs[`charge_qty_${i}`] = 'Invalid qty';
    });
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    const payload: QuoteSubmitPayload = {
      buyer_id: header.buyer_id,
      origin_airport_id: header.origin_airport_id,
      destination_airport_id: header.destination_airport_id,
      tracking_number: header.tracking_number,
      gross_weight: Number(header.gross_weight),
      volumetric_weight: Number(header.volumetric_weight) || 0,
      chargeable_weight: Number(header.chargeable_weight) || 0,
      currency_id: header.currency_id,
      etd: header.etd || null,
      eta: header.eta || null,
      goods_description: header.goods_description || null,
      charges: charges.map((c) => ({
        raw_charge_name: c.raw_charge_name,
        rate: c.rate ? Number(c.rate) : null,
        basis: c.basis,
        qty: c.qty ? Number(c.qty) : null,
        amount: Number(c.amount),
      })),
    };
    submitMutation.mutate(payload);
  };

  const hField = (key: keyof typeof header) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setHeader((p) => ({ ...p, [key]: e.target.value }));

  return (
    <div className="flex flex-col w-full relative pb-20">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop mb-4">
        <button
          onClick={() => navigate('/app/quotes')}
          className="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors font-label-sm text-label-sm mb-6 w-fit"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span> Back to Quotes
        </button>
        
        <div>
          <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2 flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">add_circle</span> New
          </p>
          <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none mb-4">Submit Quote</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
            Enter the details of your quote using your own charge terminology. LogiSight will automatically map it to the client's nomenclature.
          </p>
        </div>
      </div>

      <div className="px-spacing-margin-desktop max-w-5xl">
        {apiError && (
          <div className="flex items-center gap-3 p-4 mb-8 rounded-xl bg-error-container text-on-error-container border border-error/20">
            <span className="material-symbols-outlined text-[20px] text-error">error</span>
            <p className="font-body-md text-body-md">{apiError}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          <section className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm border border-surface-container">
            <div className="flex items-center gap-3 mb-8">
              <span className="material-symbols-outlined text-[24px] text-primary">local_shipping</span>
              <h2 className="font-headline-md-mobile text-[20px] font-semibold text-on-surface tracking-tight">Shipment Details</h2>
            </div>

            <div className="space-y-6">
              <Field label="Addressed To (Client)" error={errors.buyer_id}>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">business</span>
                  <select 
                    value={header.buyer_id} 
                    onChange={hField('buyer_id')} 
                    className={`w-full pl-11 pr-10 py-3 rounded-2xl border bg-surface text-on-surface appearance-none font-body-md transition-all focus:outline-none focus:ring-1 ${errors.buyer_id ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                  >
                    <option value="">Select client company...</option>
                    {clientCompanies.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none">expand_more</span>
                </div>
              </Field>

              <div className="grid md:grid-cols-2 gap-6">
                <Field label="Origin Airport" error={errors.origin}>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">flight_takeoff</span>
                    <select 
                      value={header.origin_airport_id} 
                      onChange={hField('origin_airport_id')} 
                      className={`w-full pl-11 pr-10 py-3 rounded-2xl border bg-surface text-on-surface appearance-none font-body-md transition-all focus:outline-none focus:ring-1 ${errors.origin ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                    >
                      <option value="">Select origin...</option>
                      {airports.map((a) => (
                        <option key={a.id} value={a.id}>{a.iata_code} — {a.name}</option>
                      ))}
                    </select>
                    <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none">expand_more</span>
                  </div>
                </Field>
                <Field label="Destination Airport" error={errors.destination}>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">flight_land</span>
                    <select 
                      value={header.destination_airport_id} 
                      onChange={hField('destination_airport_id')} 
                      className={`w-full pl-11 pr-10 py-3 rounded-2xl border bg-surface text-on-surface appearance-none font-body-md transition-all focus:outline-none focus:ring-1 ${errors.destination ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                    >
                      <option value="">Select destination...</option>
                      {airports.map((a) => (
                        <option key={a.id} value={a.id}>{a.iata_code} — {a.name}</option>
                      ))}
                    </select>
                    <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none">expand_more</span>
                  </div>
                </Field>
              </div>

              <Field label="AWB / Tracking Number" error={errors.tracking}>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">barcode</span>
                  <input
                    value={header.tracking_number}
                    onChange={hField('tracking_number')}
                    className={`w-full pl-11 pr-4 py-3 rounded-2xl border bg-surface text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 ${errors.tracking ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                    placeholder="e.g. 176-12345678"
                  />
                </div>
              </Field>

              <div className="grid md:grid-cols-2 gap-6">
                <Field label="ETD (Estimated Departure)">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">calendar_today</span>
                    <input
                      type="date"
                      value={header.etd}
                      onChange={hField('etd')}
                      className="w-full pl-11 pr-4 py-3 rounded-2xl border border-surface-container focus:border-primary bg-surface text-on-surface font-body-md transition-all focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </Field>
                <Field label="ETA (Estimated Arrival)">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">event_upcoming</span>
                    <input
                      type="date"
                      value={header.eta}
                      onChange={hField('eta')}
                      className="w-full pl-11 pr-4 py-3 rounded-2xl border border-surface-container focus:border-primary bg-surface text-on-surface font-body-md transition-all focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </Field>
              </div>

              <Field label="Goods Description">
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-4 text-on-surface-variant text-[20px]">inventory_2</span>
                  <textarea
                    value={header.goods_description}
                    onChange={hField('goods_description')}
                    placeholder="e.g., Substrate for Fuel Cell, AAC/upgrades"
                    rows={2}
                    className="w-full pl-11 pr-4 py-3 rounded-2xl border border-surface-container focus:border-primary bg-surface text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                  />
                </div>
              </Field>

              <div className="grid md:grid-cols-3 gap-6">
                <Field label="Gross Weight (kg)" error={errors.gross}>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">weight</span>
                    <input 
                      type="number" step="0.01" 
                      value={header.gross_weight} 
                      onChange={hField('gross_weight')} 
                      className={`w-full pl-11 pr-4 py-3 rounded-2xl border bg-surface text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 ${errors.gross ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`} 
                      placeholder="0.00" 
                    />
                  </div>
                </Field>
                <Field label="Volumetric Wt (kg)">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">view_in_ar</span>
                    <input 
                      type="number" step="0.01" 
                      value={header.volumetric_weight} 
                      onChange={hField('volumetric_weight')} 
                      className="w-full pl-11 pr-4 py-3 rounded-2xl border border-surface-container focus:border-primary bg-surface text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 focus:ring-primary" 
                      placeholder="0.00" 
                    />
                  </div>
                </Field>
                <Field label="Chargeable Wt (kg)">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">scale</span>
                    <input 
                      type="number" step="0.01" 
                      value={header.chargeable_weight} 
                      onChange={hField('chargeable_weight')} 
                      className="w-full pl-11 pr-4 py-3 rounded-2xl border border-surface-container focus:border-primary bg-surface text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 focus:ring-primary bg-surface-container/30" 
                      placeholder="0.00" 
                    />
                  </div>
                </Field>
              </div>

              <Field label="Currency" error={errors.currency}>
                <div className="relative w-full md:w-1/2">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">payments</span>
                  <select 
                    value={header.currency_id} 
                    onChange={hField('currency_id')} 
                    className={`w-full pl-11 pr-10 py-3 rounded-2xl border bg-surface text-on-surface appearance-none font-body-md transition-all focus:outline-none focus:ring-1 ${errors.currency ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                  >
                    <option value="">Select currency...</option>
                    {currencies.map((c) => (
                      <option key={c.id} value={c.id}>{c.short_name} — {c.name}</option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none">expand_more</span>
                </div>
              </Field>
            </div>
          </section>

          <section className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm border border-surface-container">
            <div className="flex items-center gap-3 mb-8">
              <span className="material-symbols-outlined text-[24px] text-primary">request_quote</span>
              <h2 className="font-headline-md-mobile text-[20px] font-semibold text-on-surface tracking-tight">Charge Lines</h2>
            </div>

            <div className="space-y-4">
              {charges.map((charge, idx) => (
                <div key={idx} className="p-6 rounded-2xl border border-surface-container bg-surface relative group">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-label-sm text-label-sm font-semibold text-primary uppercase tracking-widest bg-primary/10 px-3 py-1 rounded-full">
                      Charge {idx + 1}
                    </span>
                    {charges.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeCharge(idx)}
                        className="w-8 h-8 rounded-full bg-surface-container hover:bg-error-container hover:text-error text-on-surface-variant flex items-center justify-center transition-colors"
                        title="Remove charge"
                      >
                        <span className="material-symbols-outlined text-[18px]">delete</span>
                      </button>
                    )}
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Charge Name (your terminology)</label>
                      <input
                        value={charge.raw_charge_name}
                        onChange={(e) => updateCharge(idx, 'raw_charge_name', e.target.value)}
                        className={`w-full px-4 py-2.5 rounded-xl border bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 ${errors[`charge_name_${idx}`] ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                        placeholder="e.g. Fuel Levy, Bunker Surcharge..."
                      />
                      {errors[`charge_name_${idx}`] && <p className="mt-1.5 text-label-sm text-error ml-1 flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">error</span> {errors[`charge_name_${idx}`]}</p>}
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Rate (Optional)</label>
                        <input
                          type="number" step="0.01"
                          value={charge.rate}
                          onChange={(e) => updateCharge(idx, 'rate', e.target.value)}
                          className={`w-full px-4 py-2.5 rounded-xl border bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 ${errors[`charge_rate_${idx}`] ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                          placeholder="0.00"
                        />
                        {errors[`charge_rate_${idx}`] && <p className="mt-1 text-[11px] text-error ml-1">{errors[`charge_rate_${idx}`]}</p>}
                      </div>
                      
                      <div>
                        <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Basis</label>
                        <div className="relative">
                          <select
                            value={charge.basis}
                            onChange={(e) => updateCharge(idx, 'basis', e.target.value)}
                            className="w-full pl-4 pr-10 py-2.5 rounded-xl border border-surface-container focus:border-primary bg-surface-container-lowest text-on-surface appearance-none font-body-md transition-all focus:outline-none focus:ring-1 focus:ring-primary"
                          >
                            {BASIS_OPTIONS.map((b) => <option key={b}>{b}</option>)}
                          </select>
                          <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-[18px]">expand_more</span>
                        </div>
                      </div>
                      
                      <div>
                        <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Qty (Optional)</label>
                        <input
                          type="number" step="0.01"
                          value={charge.qty}
                          onChange={(e) => updateCharge(idx, 'qty', e.target.value)}
                          className={`w-full px-4 py-2.5 rounded-xl border bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant/70 font-body-md transition-all focus:outline-none focus:ring-1 ${errors[`charge_qty_${idx}`] ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                          placeholder="1.00"
                        />
                        {errors[`charge_qty_${idx}`] && <p className="mt-1 text-[11px] text-error ml-1">{errors[`charge_qty_${idx}`]}</p>}
                      </div>
                      
                      <div>
                        <label className="block font-label-sm text-label-sm text-on-surface-variant mb-2 ml-1">Amount</label>
                        <input
                          type="number" step="0.01"
                          value={charge.amount}
                          onChange={(e) => updateCharge(idx, 'amount', e.target.value)}
                          className={`w-full px-4 py-2.5 rounded-xl border bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant/70 font-body-md font-mono transition-all focus:outline-none focus:ring-1 ${errors[`charge_amount_${idx}`] ? 'border-error focus:border-error focus:ring-error' : 'border-surface-container focus:border-primary focus:ring-primary'}`}
                          placeholder="0.00"
                        />
                        {errors[`charge_amount_${idx}`] && <p className="mt-1 text-[11px] text-error ml-1">{errors[`charge_amount_${idx}`]}</p>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-col md:flex-row md:items-center justify-between mt-8 pt-6 border-t border-surface-container gap-4">
              <button
                type="button"
                onClick={addCharge}
                className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-surface-container hover:bg-surface-container text-on-surface font-label-sm text-label-sm transition-colors w-fit"
              >
                <span className="material-symbols-outlined text-[18px]">add</span> Add Charge Line
              </button>
              <div className="bg-surface px-6 py-4 rounded-2xl border border-surface-container">
                <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider block mb-1">Total Amount</span>
                <p className="font-display-md text-display-md text-primary font-mono tracking-tight leading-none">
                  {charges.reduce((s, c) => s + (parseFloat(c.amount) || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          </section>

          <div className="flex flex-col md:flex-row gap-4 justify-center pt-4 sticky bottom-6 z-10 bg-surface-container-lowest/80 backdrop-blur-md p-4 rounded-2xl border border-surface-container shadow-lg">
            <button
              type="button"
              onClick={() => navigate('/app/quotes')}
              className="flex-1 md:flex-none px-8 py-3.5 rounded-full border border-surface-container hover:bg-surface-container text-on-surface font-label-sm text-label-sm transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="flex-1 md:flex-none px-8 py-3.5 rounded-full bg-primary hover:bg-on-surface disabled:opacity-60 text-on-primary font-label-sm text-label-sm shadow-sm transition-all transform active:scale-95 flex items-center justify-center gap-2"
            >
              {submitMutation.isPending ? (
                <>
                  <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[20px]">send</span>
                  Submit Quote
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
