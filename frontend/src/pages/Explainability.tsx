import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Brain, AlertCircle, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';

export const Explainability: React.FC = () => {
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [importance, setImportance] = useState<any>(null);
  const [predictionInput, setPredictionInput] = useState<Record<string, string>>({});
  const [explanation, setExplanation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getModels().then(r => {
      const items = r.items || [];
      setModels(items);
      if (items.length > 0) setSelectedModel(items[0].id);
    });
  }, []);

  const loadImportance = async () => {
    if (!selectedModel) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.getExplainability(selectedModel);
      setImportance(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to compute importance');
    }
    setLoading(false);
  };

  const explainPrediction = async () => {
    if (!selectedModel) return;
    setLoading(true);
    setError(null);
    try {
      const features: Record<string, any> = {};
      for (const [k, v] of Object.entries(predictionInput)) {
        features[k] = isNaN(Number(v)) ? v : Number(v);
      }
      const result = await apiService.explainPrediction(selectedModel, features);
      setExplanation(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Explanation failed');
    }
    setLoading(false);
  };

  const COLORS = ['#38bdf8', '#818cf8', '#34d399', '#fbbf24', '#fb923c', '#f472b6', '#a78bfa', '#22d3ee', '#94a3b8', '#64748b'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
          <Brain className="w-7 h-7 text-purple-400" /> Model Explainability
        </h1>
        <p className="text-sm text-slate-400 mt-1">SHAP-based feature importance from actual model computation</p>
      </div>

      <div className="flex items-center gap-4">
        <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-4 py-2 text-sm">
          <option value="">Select model...</option>
          {models.map(m => <option key={m.id} value={m.id}>{m.name} (v{m.version})</option>)}
        </select>
        <button onClick={loadImportance} disabled={!selectedModel || loading}
          className="px-5 py-2 bg-purple-500 hover:bg-purple-400 text-white rounded-lg text-sm font-medium disabled:opacity-50">
          {loading ? 'Computing...' : 'Compute Feature Importance'}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {importance?.feature_importance?.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-200 mb-4">
            Global Feature Importance ({importance.method === 'shap' ? 'SHAP' : importance.method})
          </h3>
          <ResponsiveContainer width="100%" height={Math.max(300, importance.feature_importance.length * 35)}>
            <BarChart data={importance.feature_importance.slice(0, 15)} layout="vertical" margin={{ left: 120 }}>
              <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis type="category" dataKey="feature" tick={{ fontSize: 11, fill: '#cbd5e1' }} width={120} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                {importance.feature_importance.slice(0, 15).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {importance.warning && (
            <p className="text-xs text-amber-400 mt-3 inline-flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" />{importance.warning}</p>
          )}
              {importance.parquet_path && (
                <div className="mt-3 text-[11px] font-mono text-slate-500 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-sky-400"></span>
                  <span>Parquet Archive: {importance.parquet_path}</span>
                </div>
              )}
            </div>
          )}

          {/* Individual Prediction Explanation with SHAP Waterfall Chart */}
          {selectedModel && importance && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-200">Explain Individual Prediction</h3>
                <p className="text-xs text-slate-400 mt-0.5">Input custom values to inspect feature contributions in real-time.</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {importance.top_features?.slice(0, 8).map((feat: string) => (
                  <div key={feat}>
                    <label className="text-xs text-slate-400 block mb-1">{feat}</label>
                    <input
                      type="text"
                      value={predictionInput[feat] || ''}
                      onChange={e => setPredictionInput(prev => ({ ...prev, [feat]: e.target.value }))}
                      className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 text-sm"
                      placeholder="Enter value"
                    />
                  </div>
                ))}
              </div>

              <button onClick={explainPrediction} disabled={loading}
                className="px-5 py-2 bg-sky-500 hover:bg-sky-400 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                {loading ? 'Analyzing...' : 'Generate Waterfall Explanation'}
              </button>

              {explanation?.status === 'success' && (
                <div className="mt-4 space-y-5 pt-4 border-t border-slate-800">
                  <div className="flex items-center gap-6 p-4 bg-slate-950 rounded-xl border border-slate-800">
                    <div>
                      <span className="text-xs text-slate-500 block">Final Model Output</span>
                      <span className="text-xl font-bold text-sky-400">{explanation.prediction}</span>
                    </div>
                    {explanation.probability && (
                      <div>
                        <span className="text-xs text-slate-500 block">Confidence Score</span>
                        <span className="text-xl font-bold text-purple-400">{explanation.probability}</span>
                      </div>
                    )}
                    {explanation.base_value !== undefined && (
                      <div>
                        <span className="text-xs text-slate-500 block">Base Value E[f(X)]</span>
                        <span className="text-xl font-bold text-slate-300">{Number(explanation.base_value).toFixed(4)}</span>
                      </div>
                    )}
                  </div>

                  {/* SHAP Waterfall Chart */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                        SHAP Waterfall Progression
                      </h4>
                      <div className="flex items-center gap-3 text-[11px]">
                        <span className="flex items-center gap-1 text-rose-400">
                          <span className="w-2.5 h-2.5 rounded bg-rose-500"></span> Positive (+ higher)
                        </span>
                        <span className="flex items-center gap-1 text-cyan-400">
                          <span className="w-2.5 h-2.5 rounded bg-cyan-500"></span> Negative (- lower)
                        </span>
                      </div>
                    </div>

                    <div className="h-64 w-full bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={(explanation.contributions || []).slice(0, 8).map((c: any) => ({
                            feature: c.feature,
                            shap_value: c.shap_value,
                            abs_val: Math.abs(c.shap_value),
                            direction: c.shap_value >= 0 ? 'positive' : 'negative',
                          }))}
                          layout="vertical"
                          margin={{ left: 100, right: 30 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis type="number" stroke="#64748b" fontSize={10} />
                          <YAxis type="category" dataKey="feature" stroke="#94a3b8" fontSize={11} width={100} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                            formatter={(v: any) => [`${v}`, 'SHAP Value']}
                          />
                          <Bar dataKey="shap_value" radius={[0, 4, 4, 0]}>
                            {(explanation.contributions || []).slice(0, 8).map((entry: any, i: number) => (
                              <Cell key={i} fill={entry.shap_value >= 0 ? '#f43f5e' : '#06b6d4'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Feature Contributions List */}
                  <div className="space-y-1.5 pt-2">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase">Feature Contribution Details</h4>
                    <div className="divide-y divide-slate-800/60 rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden">
                      {explanation.contributions?.slice(0, 10).map((c: any, i: number) => (
                        <div key={i} className="flex items-center justify-between px-4 py-2 hover:bg-slate-800/20">
                          <span className="text-xs text-slate-300 font-medium">{c.feature}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-slate-500 font-mono">val: {String(c.value)}</span>
                            <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                              c.shap_value >= 0 ? 'bg-rose-500/15 text-rose-400' : 'bg-cyan-500/15 text-cyan-400'
                            }`}>
                              {c.shap_value >= 0 ? '+' : ''}{Number(c.shap_value).toFixed(4)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

      {!importance && !loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <Brain className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-semibold text-slate-300">No Explanations Yet</h3>
          <p className="text-sm text-slate-500">Select a model and compute feature importance</p>
        </div>
      )}
    </div>
  );
};
