import React, { useState, useEffect, useRef } from 'react';
import { Bell, CheckCircle2, ShieldAlert, X } from 'lucide-react';
import { apiService } from '../services/api';

export const AlertBell: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchAlerts = async () => {
    try {
      const data = await apiService.getAlerts();
      if (Array.isArray(data)) {
        setAlerts(data.filter((a) => !a.is_resolved));
      }
    } catch {
      // Backend may not have alerts yet
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 20000);
    return () => clearInterval(interval);
  }, []);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleResolve = async (id: string) => {
    setResolvingId(id);
    try {
      await apiService.resolveAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error('Failed to resolve alert:', err);
    } finally {
      setResolvingId(null);
    }
  };

  const count = alerts.length;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        title="Drift & System Alerts"
        className="relative p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition-all"
      >
        <Bell className="w-4 h-4" />
        {count > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-lg shadow-rose-500/50">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-slate-950 border border-slate-800 shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Monitoring Alerts ({count})
              </h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-slate-500 hover:text-slate-300"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-3 max-h-72 overflow-y-auto space-y-2.5">
            {alerts.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 flex flex-col items-center gap-2">
                <CheckCircle2 className="w-6 h-6 text-emerald-500/60" />
                <span>All systems healthy. No active drift alerts.</span>
              </div>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between gap-2"
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                          a.severity === 'critical'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}
                      >
                        {a.severity || 'alert'}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {a.created_at ? new Date(a.created_at).toLocaleTimeString() : ''}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-snug">{a.message}</p>
                  </div>

                  <div className="flex justify-end pt-1">
                    <button
                      onClick={() => handleResolve(a.id)}
                      disabled={resolvingId === a.id}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                    >
                      {resolvingId === a.id ? 'Resolving...' : 'Dismiss / Resolve'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
