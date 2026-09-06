import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Box, Shield, Archive, Rocket, RefreshCw, ArrowRight } from 'lucide-react';

export const Models: React.FC = () => {
  const user = useAuthStore((s) => s.user);
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    if (!user) {
      setModels([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    apiService.getModels().then(r => setModels(r.items || [])).finally(() => setLoading(false));
  };
  useEffect(load, [user]);

  const statusColors: Record<string, string> = {
    TRAINED: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    VALIDATED: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    STAGING: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    PRODUCTION: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    ARCHIVED: 'bg-slate-700/30 text-slate-400 border-slate-600/30',
  };

  const deploy = async (modelId: string) => {
    try {
      await apiService.deployModel(modelId);
      load();
    } catch (err: any) { alert(err.response?.data?.detail || 'Deploy failed'); }
  };

  const updateStatus = async (modelId: string, status: string) => {
    try {
      await apiService.updateModelStatus(modelId, status);
      load();
    } catch (err: any) { alert(err.response?.data?.detail || 'Update failed'); }
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Box className="w-5 h-5 text-emerald-400" />
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Registry</span>
          </div>
          <h1 className="text-3xl font-black text-slate-100 tracking-tight">Model Registry</h1>
          <p className="text-sm text-slate-400 mt-1">Manage trained models — promote, deploy, archive</p>
        </div>
        <button onClick={load} className="p-2.5 text-slate-400 hover:text-slate-200 rounded-xl hover:bg-slate-800/50 border border-slate-800/50 transition-all">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading && (
        <div className="space-y-4 animate-fade-in">
          {[1,2,3].map(i => <div key={i} className="skeleton h-32 rounded-2xl" />)}
        </div>
      )}

      {!loading && models.length > 0 ? (
        <div className="space-y-4">
          {models.map((model, idx) => (
            <div key={model.id}
              className={`animate-fade-in-up stagger-${Math.min(idx + 1, 8)} glass-card border border-slate-800/50 rounded-2xl p-5 card-hover transition-all`}>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-base font-semibold text-slate-200">{model.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">v{model.version} • {model.algorithm} • {model.task_type}</p>
                </div>
                <span className={`px-3 py-1 rounded-xl text-xs font-semibold border ${statusColors[model.status] || statusColors.TRAINED}`}>
                  {model.status === 'PRODUCTION' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />}
                  {model.status}
                </span>
              </div>

              {/* Metrics */}
              {model.metrics && (
                <div className="flex flex-wrap gap-2.5 mb-4">
                  {Object.entries(model.metrics).map(([key, val]: [string, any]) => (
                    <div key={key} className="bg-slate-900/40 border border-slate-800/30 rounded-xl px-3 py-1.5">
                      <span className="text-[10px] text-slate-400 uppercase">{key}</span>
                      <span className="text-sm font-mono text-slate-200 ml-2 font-semibold">{typeof val === 'number' ? val.toFixed(4) : val}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                {model.status !== 'PRODUCTION' && model.status !== 'ARCHIVED' && (
                  <button onClick={() => deploy(model.id)}
                    className="text-xs px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl hover:bg-emerald-500/20 flex items-center gap-1 transition-all">
                    <Rocket className="w-3 h-3" /> Deploy
                  </button>
                )}
                {model.status !== 'PRODUCTION' && model.status !== 'ARCHIVED' && (
                  <button onClick={() => updateStatus(model.id, 'STAGING')}
                    className="text-xs px-3 py-1.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-xl hover:bg-amber-500/20 flex items-center gap-1 transition-all">
                    <Shield className="w-3 h-3" /> Promote to Staging
                  </button>
                )}
                {model.status !== 'ARCHIVED' && (
                  <button onClick={() => updateStatus(model.id, 'ARCHIVED')}
                    className="text-xs px-3 py-1.5 bg-slate-700/30 text-slate-400 border border-slate-600/30 rounded-xl hover:bg-slate-700/50 flex items-center gap-1 transition-all">
                    <Archive className="w-3 h-3" /> Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : !loading ? (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
            <Box className="w-8 h-8 text-emerald-400/60" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Models Registered</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">Train experiments first, then register the best models here</p>
          <div className="flex items-center justify-center gap-2 text-emerald-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Go to Experiments to train models</span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
