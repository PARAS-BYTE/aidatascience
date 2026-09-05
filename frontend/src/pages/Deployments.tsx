import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { 
  Rocket, StopCircle, RefreshCw, ExternalLink, ArrowRight, 
  Award, FileText, X, Check, Copy, Code2
} from 'lucide-react';

export const Deployments: React.FC = () => {
  const [deployments, setDeployments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCard, setSelectedCard] = useState<any | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const apiBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

  const copySnippet = async (key: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(key);
    window.setTimeout(() => setCopied(null), 1800);
  };

  const load = () => {
    setLoading(true);
    apiService.getDeployments().then(r => setDeployments(r.items || [])).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const stopDeployment = async (id: string) => {
    try {
      await apiService.stopDeployment(id);
      load();
    } catch (err: any) { alert(err.response?.data?.detail || 'Failed to stop'); }
  };

  const handlePromote = async (deploymentId: string) => {
    try {
      await apiService.promoteChallenger(deploymentId);
      setActionSuccess('Challenger successfully promoted to Champion!');
      setTimeout(() => setActionSuccess(null), 4000);
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to promote challenger');
    }
  };

  const handleViewModelCard = async (modelId: string) => {
    try {
      const res = await apiService.getModelCard(modelId);
      setSelectedCard(res.content_md);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load model card');
    }
  };

  const statusColors: Record<string, string> = {
    ACTIVE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    DEPLOYING: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    FAILED: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    STOPPED: 'bg-slate-700/30 text-slate-400 border-slate-600/30',
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Rocket className="w-5 h-5 text-sky-400" />
            <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">Infrastructure & Governance</span>
          </div>
          <h1 className="text-3xl font-black text-slate-100 tracking-tight">Deployments & Champion/Challenger</h1>
          <p className="text-sm text-slate-400 mt-1">Live model serving with canary/shadow routing and Model Cards</p>
        </div>
        <button onClick={load} className="p-2.5 text-slate-400 hover:text-slate-200 rounded-xl hover:bg-slate-800/50 border border-slate-800/50 transition-all">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-2 animate-fade-in">
          <Check className="w-4 h-4" /> {actionSuccess}
        </div>
      )}

      {loading && (
        <div className="space-y-4 animate-fade-in">
          {[1,2].map(i => <div key={i} className="skeleton h-28 rounded-2xl" />)}
        </div>
      )}

      {!loading && deployments.length > 0 ? (
        <div className="space-y-4">
          {deployments.map((dep, idx) => {
            const isChampion = dep.role === 'champion' || !dep.role;
            return (
              <div key={dep.id}
                className={`animate-fade-in-up stagger-${Math.min(idx + 1, 8)} glass-card border border-slate-800/50 rounded-2xl p-5 card-hover transition-all relative overflow-hidden ${
                  dep.status === 'ACTIVE' 
                    ? isChampion ? 'border-amber-500/30 bg-gradient-to-r from-amber-500/5 via-transparent to-transparent' : 'border-sky-500/30 bg-gradient-to-r from-sky-500/5 via-transparent to-transparent'
                    : ''
                }`}>
                <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-xl text-xs font-semibold border ${statusColors[dep.status] || statusColors.STOPPED}`}>
                      {dep.status === 'ACTIVE' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />}
                      {dep.status}
                    </span>

                    {/* Champion vs Challenger badge */}
                    <span className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center gap-1.5 border ${
                      isChampion 
                        ? 'bg-amber-500/15 text-amber-300 border-amber-500/40' 
                        : 'bg-sky-500/15 text-sky-300 border-sky-500/40'
                    }`}>
                      <Award className="w-3.5 h-3.5" />
                      {isChampion ? 'Champion' : 'Challenger'}
                    </span>

                    {/* Traffic percentage */}
                    <span className="text-xs text-slate-400 font-mono px-2 py-0.5 rounded-lg bg-slate-900 border border-slate-800">
                      Traffic: {Math.round((dep.traffic_pct || 1.0) * 100)}%
                    </span>

                    <span className="text-sm font-semibold text-slate-200">Model v{dep.model_version}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* View Model Card Button */}
                    <button
                      onClick={() => handleViewModelCard(dep.model_id)}
                      className="text-xs px-3 py-1.5 bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-xl hover:bg-slate-700 flex items-center gap-1.5 transition-all"
                    >
                      <FileText className="w-3.5 h-3.5 text-sky-400" /> Model Card
                    </button>

                    {/* Promote Challenger Button */}
                    {!isChampion && dep.status === 'ACTIVE' && (
                      <button
                        onClick={() => handlePromote(dep.id)}
                        className="text-xs px-3 py-1.5 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-500/20 flex items-center gap-1 transition-all"
                      >
                        <Award className="w-3.5 h-3.5" /> Promote to Champion
                      </button>
                    )}

                    {dep.status === 'ACTIVE' && (
                      <button onClick={() => stopDeployment(dep.id)}
                        className="text-xs px-3 py-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-xl hover:bg-rose-500/20 flex items-center gap-1 transition-all">
                        <StopCircle className="w-3 h-3" /> Stop
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/30">
                    <p className="text-[10px] text-slate-400 uppercase font-medium">Endpoint</p>
                    <p className="text-sm text-sky-400 font-mono flex items-center gap-1 mt-1">
                      {dep.endpoint || 'N/A'} <ExternalLink className="w-3 h-3" />
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/30">
                    <p className="text-[10px] text-slate-400 uppercase font-medium">Inference Requests</p>
                    <p className="text-sm text-slate-200 font-mono mt-1 font-semibold">{dep.request_count?.toLocaleString()}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/30">
                    <p className="text-[10px] text-slate-400 uppercase font-medium">Deployed On</p>
                    <p className="text-sm text-slate-300 mt-1">{new Date(dep.created_at).toLocaleString()}</p>
                  </div>
                </div>

                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Code2 className="w-4 h-4 text-blue-600" />
                      <div>
                        <h3 className="text-sm font-semibold text-slate-900">Use this model API</h3>
                        <p className="text-xs text-slate-500">Send a JSON object containing a <code>features</code> object. Its keys must match the model’s input columns.</p>
                      </div>
                    </div>
                    <button onClick={() => copySnippet(`url-${dep.id}`, `${apiBaseUrl}/models/${dep.model_id}/predict`)} className="shrink-0 inline-flex items-center gap-1.5 text-xs font-medium text-blue-700 hover:text-blue-800">
                      {copied === `url-${dep.id}` ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} Copy URL
                    </button>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-3 overflow-x-auto">
                    <code className="text-xs text-slate-100 whitespace-nowrap">POST {apiBaseUrl}/models/{dep.model_id}/predict</code>
                  </div>
                  <div className="grid lg:grid-cols-2 gap-3">
                    <div className="rounded-lg border border-slate-200 bg-white p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Request body</p>
                      <pre className="text-xs leading-5 text-slate-700 overflow-x-auto">{`{
  "features": {
    "feature_name": 123,
    "category_name": "example"
  }
}`}</pre>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">cURL example</p>
                      <pre className="text-xs leading-5 text-slate-700 overflow-x-auto">{`curl -X POST "${apiBaseUrl}/models/${dep.model_id}/predict" \\
  -H "Content-Type: application/json" \\
  -d '{"features":{"feature_name":123,"category_name":"example"}}'`}</pre>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500">Replace the example keys and values with the feature names and valid values from this model’s Model Card.</p>
                </div>
              </div>
            );
          })}
        </div>
      ) : !loading ? (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mx-auto animate-float">
            <Rocket className="w-8 h-8 text-sky-400/60" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Active Deployments</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">Deploy models from the Model Registry to start serving predictions</p>
          <div className="flex items-center justify-center gap-2 text-sky-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Go to Models to deploy</span>
          </div>
        </div>
      ) : null}

      {/* Model Card Modal */}
      {selectedCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-6 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-sky-400" />
                <h3 className="text-base font-bold text-slate-100">Standardized Model Card</h3>
              </div>
              <button onClick={() => setSelectedCard(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1 pr-2 space-y-4 text-slate-300 text-xs leading-relaxed font-sans">
              <pre className="whitespace-pre-wrap font-sans bg-slate-950/60 p-4 rounded-xl border border-slate-800 text-slate-300">
                {selectedCard}
              </pre>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-800 mt-2">
              <button
                onClick={() => setSelectedCard(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
