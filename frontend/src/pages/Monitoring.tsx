import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Activity, AlertTriangle, CheckCircle2, RefreshCw, Loader2, ArrowRight, Shield } from 'lucide-react';

export const Monitoring: React.FC = () => {
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [health, setHealth] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [driftLoading, setDriftLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getModels().then(r => {
      const list = r.items || [];
      setModels(list);
      if (list.length > 0) setSelectedModel(list[0].id);
    });
  }, []);

  const loadAlerts = async (modelId = selectedModel) => {
    if (!modelId) return;
    try {
      const list = await apiService.getAlerts(modelId);
      if (Array.isArray(list)) {
        setAlerts(list);
      }
    } catch {
      // Ignored
    }
  };

  const loadHealth = async () => {
    if (!selectedModel) return;
    setLoading(true);
    setError(null);
    try {
      const h = await apiService.getModelHealth(selectedModel);
      setHealth(h);
      loadAlerts(selectedModel);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load health');
    }
    setLoading(false);
  };

  const computeDrift = async () => {
    if (!selectedModel) return;
    setDriftLoading(true);
    setError(null);
    try {
      const result = await apiService.computeDrift(selectedModel);
      setHealth(result);
      loadAlerts(selectedModel);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Drift computation failed');
    }
    setDriftLoading(false);
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      await apiService.resolveAlert(alertId);
      loadAlerts(selectedModel);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { if (selectedModel) loadHealth(); }, [selectedModel]);

  const overallHealth = health?.overall_health || health?.status || 'unknown';
  const healthColor = overallHealth === 'healthy' ? 'emerald' : overallHealth === 'warning' ? 'amber' : overallHealth === 'critical' ? 'rose' : 'slate';

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-2 mb-1">
          <Activity className="w-5 h-5 text-sky-400" />
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">Observability</span>
        </div>
        <h1 className="text-3xl font-black text-slate-100 tracking-tight">Model Monitoring</h1>
        <p className="text-sm text-slate-400 mt-1">Health, drift detection, and prediction monitoring</p>
      </div>

      {/* Controls */}
      <div className="animate-fade-in-up stagger-1 flex items-center gap-4">
        <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
          className="bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:border-sky-500/50 transition-colors">
          <option value="">Select model...</option>
          {models.map(m => <option key={m.id} value={m.id}>{m.name} (v{m.version})</option>)}
        </select>
        <button onClick={loadHealth} disabled={!selectedModel || loading}
          className="px-4 py-2.5 bg-slate-800/60 text-slate-300 rounded-xl text-sm font-medium hover:bg-slate-800 border border-slate-700/50 disabled:opacity-50 flex items-center gap-2 transition-all">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Refresh
        </button>
        <button onClick={computeDrift} disabled={!selectedModel || driftLoading}
          className="px-5 py-2.5 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white rounded-xl text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-sky-500/20 transition-all">
          {driftLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
          {driftLoading ? 'Computing...' : 'Compute Drift'}
        </button>
      </div>

      {error && (
        <div className="animate-fade-in p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" /> {error}
        </div>
      )}

      {loading && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid grid-cols-3 gap-4">
            {[1,2,3].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
          </div>
        </div>
      )}

      {health && !loading && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Health Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className={`glass-card border rounded-2xl p-5 border-${healthColor}-500/20`}>
              <p className="text-xs text-slate-400 uppercase font-semibold">Overall Health</p>
              <div className="flex items-center gap-2 mt-2">
                <div className={`w-4 h-4 rounded-full bg-${healthColor}-400 ${overallHealth !== 'unknown' ? 'animate-pulse' : ''}`} />
                <span className={`text-xl font-bold text-${healthColor}-400 capitalize`}>{overallHealth}</span>
              </div>
            </div>
            <div className="glass-card border border-slate-800/50 rounded-2xl p-5">
              <p className="text-xs text-slate-400 uppercase font-semibold">Total Predictions</p>
              <p className="text-2xl font-bold text-slate-100 mt-2">{(health.total_predictions || 0).toLocaleString()}</p>
            </div>
            <div className="glass-card border border-slate-800/50 rounded-2xl p-5">
              <p className="text-xs text-slate-400 uppercase font-semibold">Avg Latency</p>
              <p className="text-2xl font-bold text-slate-100 mt-2">{health.avg_latency_ms?.toFixed(1) || '—'} ms</p>
            </div>
          </div>

          {/* Drift Results */}
          {health.drift_features?.length > 0 && (
            <div className="glass-card border border-slate-800/50 rounded-2xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                <Shield className="w-4 h-4 text-sky-400" /> Feature Drift Analysis
              </h3>
              <div className="space-y-3">
                {health.drift_features.map((f: any, idx: number) => {
                  const drifted = f.p_value < 0.05 || f.drifted;
                  return (
                    <div key={f.feature || idx} className={`animate-fade-in-up stagger-${Math.min(idx + 1, 8)} flex items-center justify-between p-3.5 rounded-xl border transition-all ${
                      drifted ? 'bg-rose-500/5 border-rose-500/20' : 'bg-emerald-500/5 border-emerald-500/20'
                    }`}>
                      <div className="flex items-center gap-3">
                        {drifted ? <AlertTriangle className="w-4 h-4 text-rose-400" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                        <span className="text-sm font-medium text-slate-200">{f.feature}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        {f.psi_score !== undefined && (
                          <span className={`text-[11px] font-mono px-2 py-0.5 rounded ${
                            f.psi_score >= 0.2 ? 'bg-rose-500/20 text-rose-300' : f.psi_score >= 0.1 ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'
                          }`}>
                            PSI: {f.psi_score.toFixed(4)}
                          </span>
                        )}
                        <span className="text-xs text-slate-400 font-mono">
                          p={typeof f.p_value === 'number' ? f.p_value.toFixed(4) : f.p_value}
                        </span>
                        <span className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold ${
                          drifted ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'
                        }`}>
                          {drifted ? 'DRIFT DETECTED' : 'STABLE'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Active Drift & Quality Alerts */}
          {alerts.length > 0 && (
            <div className="glass-card border border-slate-800/50 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  Active Production Alerts ({alerts.filter(a => !a.is_resolved).length})
                </h3>
                <span className="text-xs text-slate-500 font-mono">Auto-generated by Drift/Validation Watcher</span>
              </div>

              <div className="space-y-2">
                {alerts.map((a: any) => (
                  <div
                    key={a.id}
                    className={`p-3.5 rounded-xl border flex items-center justify-between gap-4 transition-all ${
                      a.is_resolved
                        ? 'bg-slate-900/40 border-slate-800/40 opacity-60'
                        : a.severity === 'critical'
                        ? 'bg-rose-950/20 border-rose-500/40'
                        : 'bg-amber-950/20 border-amber-500/40'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                          a.severity === 'critical'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}>
                          {a.severity}
                        </span>
                        <span className="text-xs text-slate-200 font-medium">{a.message}</span>
                      </div>
                      <p className="text-[10px] text-slate-500 font-mono">
                        Triggered: {a.created_at ? new Date(a.created_at).toLocaleString() : 'Just now'}
                      </p>
                    </div>

                    {!a.is_resolved ? (
                      <button
                        onClick={() => handleResolveAlert(a.id)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-colors shrink-0"
                      >
                        Dismiss
                      </button>
                    ) : (
                      <span className="text-[11px] text-emerald-400 font-medium shrink-0 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!health && !loading && (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mx-auto">
            <Activity className="w-8 h-8 text-sky-400/60" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Monitoring Data</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">Select a model and click Refresh to view health metrics</p>
          <div className="flex items-center justify-center gap-2 text-sky-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Choose a model above</span>
          </div>
        </div>
      )}
    </div>
  );
};
