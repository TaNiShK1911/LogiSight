import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTracking, getTrackingEvents } from '../api/client';
import type { TrackingShipment } from '../api/types';

const STATUS_COLORS: Record<string, string> = {
  IN_TRANSIT: 'bg-primary/10 text-primary',
  DELIVERED: 'bg-emerald-500/10 text-emerald-500',
  CUSTOMS: 'bg-amber-500/10 text-amber-500',
  DELAYED: 'bg-error-container text-on-error-container',
  PICKED_UP: 'bg-surface-container-high text-on-surface',
};

function EventTimeline({ quoteId }: { quoteId: number }) {
  const { data: events = [], isLoading } = useQuery({
    queryKey: ['tracking-events', quoteId],
    queryFn: () => getTrackingEvents(quoteId),
  });

  if (isLoading) {
    return (
      <div className="p-8 space-y-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-4">
             <div className="w-10 h-10 rounded-full bg-surface-container animate-pulse shrink-0" />
             <div className="flex-1 space-y-2 pt-2">
                <div className="h-4 w-32 bg-surface-container animate-pulse rounded" />
                <div className="h-3 w-48 bg-surface-container-highest animate-pulse rounded" />
             </div>
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="p-12 text-center">
        <span className="material-symbols-outlined text-[40px] text-outline-variant mb-4">pending_actions</span>
        <p className="font-body-md text-body-md text-on-surface-variant">No tracking events recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="px-8 pb-8 pt-6">
      <div className="relative">
        <div className="absolute left-[19px] top-4 bottom-4 w-px bg-surface-container-high" />
        <ul className="space-y-6">
          {events.map((event, idx) => (
            <li key={event.id} className="relative flex gap-6">
              <div
                className={`w-10 h-10 rounded-full border-[3px] flex items-center justify-center flex-shrink-0 z-10 transition-colors ${
                  idx === 0
                    ? 'border-primary/20 bg-primary/10 text-primary'
                    : 'border-surface-container bg-surface-container-lowest text-outline-variant'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">
                   {idx === 0 ? 'my_location' : 'check_circle'}
                </span>
              </div>
              <div className="flex-1 pt-1.5 pb-2">
                <div className="flex items-center gap-3 mb-1">
                  <span className={`font-label-sm text-label-sm tracking-wide uppercase ${idx === 0 ? 'text-primary font-bold' : 'text-on-surface font-semibold'}`}>
                    {event.status}
                  </span>
                  <span className="font-label-sm text-[12px] text-outline-variant flex items-center gap-1 bg-surface px-2 py-0.5 rounded-full border border-surface-container">
                    <span className="material-symbols-outlined text-[14px]">schedule</span>
                    {new Date(event.event_time).toLocaleString()}
                  </span>
                </div>
                <p className="font-body-md text-body-md text-on-surface-variant mb-2 leading-relaxed">{event.description}</p>
                <p className="font-label-sm text-[13px] text-on-surface-variant flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] text-primary/70">location_on</span> {event.location}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ShipmentRow({ shipment }: { shipment: TrackingShipment }) {
  const [expanded, setExpanded] = useState(false);
  const statusCls = STATUS_COLORS[shipment.current_status] ?? 'bg-surface-container-high text-on-surface border-outline-variant';

  return (
    <div className="border border-surface-container rounded-3xl overflow-hidden bg-surface-container-lowest shadow-sm transition-all duration-200 hover:shadow-md">
      <div
        className="flex items-center gap-4 px-6 py-5 cursor-pointer hover:bg-surface-container/30 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className={`w-8 h-8 rounded-full flex items-center justify-center bg-surface transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}>
           <span className="material-symbols-outlined text-[20px] text-on-surface-variant">chevron_right</span>
        </div>
        
        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
          <div>
            <p className="font-label-sm text-[11px] text-outline-variant uppercase tracking-widest mb-1 flex items-center gap-1">
               <span className="material-symbols-outlined text-[14px]">barcode</span> AWB
            </p>
            <p className="font-mono font-medium text-[15px] text-primary bg-primary/5 px-2 py-0.5 rounded w-fit">{shipment.tracking_number}</p>
          </div>
          <div>
            <p className="font-label-sm text-[11px] text-outline-variant uppercase tracking-widest mb-1 flex items-center gap-1">
               <span className="material-symbols-outlined text-[14px]">route</span> Route
            </p>
            <div className="flex items-center gap-2">
               <span className="font-body-md text-body-md text-on-surface font-medium">{shipment.origin}</span>
               <span className="material-symbols-outlined text-[16px] text-outline-variant">arrow_right_alt</span>
               <span className="font-body-md text-body-md text-on-surface font-medium">{shipment.destination}</span>
            </div>
          </div>
          <div>
            <p className="font-label-sm text-[11px] text-outline-variant uppercase tracking-widest mb-1 flex items-center gap-1">
               <span className="material-symbols-outlined text-[14px]">local_shipping</span> Forwarder
            </p>
            <p className="font-body-md text-body-md text-on-surface">{shipment.forwarder_name}</p>
          </div>
          <div className="flex items-center justify-end md:justify-start">
            <span className={`px-3 py-1.5 rounded-full font-label-sm text-[12px] uppercase tracking-wider font-bold ${statusCls}`}>
              {shipment.current_status.replace('_', ' ')}
            </span>
          </div>
        </div>
      </div>
      
      {/* Animated collapse logic */}
      <div className={`grid transition-all duration-300 ease-in-out ${expanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
         <div className="overflow-hidden">
            <div className="border-t border-surface-container bg-surface-container-lowest/50">
              <EventTimeline quoteId={shipment.quote_id} />
            </div>
         </div>
      </div>
    </div>
  );
}

export function Tracking() {
  const { data: shipments = [], isLoading } = useQuery({
    queryKey: ['tracking'],
    queryFn: getTracking,
  });

  return (
    <div className="flex flex-col w-full px-spacing-margin-desktop py-spacing-margin-desktop relative pb-10">
      <div className="mb-8">
        <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px]">explore</span> Logistics
        </p>
        <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none mb-3">Shipment Tracking</h1>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
          Live status and event history for all active shipments.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4 max-w-5xl">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-3xl bg-surface-container-lowest border border-surface-container animate-pulse shadow-sm" />
          ))}
        </div>
      ) : shipments.length === 0 ? (
        <div className="py-24 flex flex-col items-center justify-center bg-surface-container-lowest rounded-3xl border border-surface-container border-dashed max-w-5xl">
          <div className="w-20 h-20 bg-surface rounded-full flex items-center justify-center mb-6">
             <span className="material-symbols-outlined text-[40px] text-outline-variant">location_off</span>
          </div>
          <h2 className="font-headline-md-mobile text-[24px] font-semibold text-on-surface mb-2">No active shipments</h2>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-md text-center">
             You don't have any shipments being tracked at the moment. Accepted quotes will appear here automatically.
          </p>
        </div>
      ) : (
        <div className="space-y-4 max-w-5xl">
          {shipments.map((s) => (
            <ShipmentRow key={s.quote_id} shipment={s} />
          ))}
        </div>
      )}
    </div>
  );
}
