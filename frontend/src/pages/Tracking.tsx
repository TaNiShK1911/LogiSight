import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapPin, ChevronDown, ChevronRight, Clock } from 'lucide-react';
import { getTracking, getTrackingEvents } from '../api/client';
import type { TrackingShipment } from '../api/types';

const STATUS_COLORS: Record<string, string> = {
  IN_TRANSIT: 'bg-sky-900/60 text-sky-300 border-sky-800',
  DELIVERED: 'bg-emerald-900/60 text-emerald-300 border-emerald-800',
  CUSTOMS: 'bg-amber-900/60 text-amber-300 border-amber-800',
  DELAYED: 'bg-red-900/60 text-red-300 border-red-800',
  PICKED_UP: 'bg-slate-800 text-slate-300 border-slate-700',
};

function EventTimeline({ quoteId }: { quoteId: number }) {
  const { data: events = [], isLoading } = useQuery({
    queryKey: ['tracking-events', quoteId],
    queryFn: () => getTrackingEvents(quoteId),
  });

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 rounded bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return <p className="px-4 py-3 text-sm text-slate-500 italic">No tracking events recorded yet.</p>;
  }

  return (
    <div className="px-5 pb-5 pt-3">
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-px bg-slate-800" />
        <ul className="space-y-4">
          {events.map((event, idx) => (
            <li key={event.id} className="relative flex gap-4">
              <div
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 z-10 ${
                  idx === 0
                    ? 'border-sky-500 bg-sky-950'
                    : 'border-slate-700 bg-slate-900'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${idx === 0 ? 'bg-sky-400' : 'bg-slate-600'}`} />
              </div>
              <div className="flex-1 pb-2">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-sm font-semibold ${idx === 0 ? 'text-sky-300' : 'text-slate-200'}`}>
                    {event.status}
                  </span>
                  <span className="text-xs text-slate-600 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(event.event_time).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{event.description}</p>
                <p className="text-xs text-slate-600 mt-0.5 flex items-center gap-1">
                  <MapPin className="w-3 h-3" /> {event.location}
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
  const statusCls = STATUS_COLORS[shipment.current_status] ?? 'bg-slate-800 text-slate-300 border-slate-700';

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
        <div className="flex-1 grid grid-cols-4 gap-4 items-center">
          <div>
            <p className="text-xs text-slate-500 mb-0.5">AWB</p>
            <p className="font-mono text-sm text-sky-400 font-medium">{shipment.tracking_number}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Route</p>
            <p className="text-sm text-slate-300">{shipment.origin} → {shipment.destination}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Forwarder</p>
            <p className="text-sm text-slate-300">{shipment.forwarder_name}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-full border text-xs font-semibold ${statusCls}`}>
              {shipment.current_status.replace('_', ' ')}
            </span>
          </div>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-slate-800 bg-slate-900/30">
          <EventTimeline quoteId={shipment.quote_id} />
        </div>
      )}
    </div>
  );
}

export function Tracking() {
  const { data: shipments = [], isLoading } = useQuery({
    queryKey: ['tracking'],
    queryFn: getTracking,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Shipment Tracking</h1>
        <p className="text-slate-400 mt-1 text-sm">Live status and event history for all active shipments</p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
          ))}
        </div>
      ) : shipments.length === 0 ? (
        <div className="py-24 text-center">
          <MapPin className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-400 font-medium">No shipments tracked yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {shipments.map((s) => (
            <ShipmentRow key={s.quote_id} shipment={s} />
          ))}
        </div>
      )}
    </div>
  );
}
