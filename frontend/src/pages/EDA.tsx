import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { BarChart3, AlertCircle, Loader2, ArrowRight, Zap, Sparkles, AlertTriangle, CheckCircle2, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export const EDA: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [eda, setEda] = useState<any>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getDatasets().then(r => {
      setDatasets(r.items || []);
      if (r.items?.length > 0) setSelectedDataset(r.items[0].id);
    });
  }, []);

  const loadInsights = async (datasetId: string) => {
    try {
      const res = await apiService.getInsights(datasetId);
      setInsights(res.insights || []);
    } catch (e) {
      console.error("Failed to load insights", e);
    }
  };

  useEffect(() => {
    if (selectedDataset) {
      loadInsights(selectedDataset);
    }
  }, [selectedDataset]);

  const runEda = async () => {
    if (!selectedDataset) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.runEda(selectedDataset);
      setEda(result);
      await loadInsights(selectedDataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'EDA failed');
    }
    setLoading(false);
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return {
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          badge: 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
          icon: <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
        };
      case 'high':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          badge: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
          icon: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
        };
      case 'medium':
        return {
          bg: 'bg-sky-500/10 border-sky-500/30 text-sky-400',
          badge: 'bg-sky-500/20 text-sky-300 border border-sky-500/30',
          icon: <AlertCircle className="w-4 h-4 text-sky-400 shrink-0" />
        };
      default:
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          badge: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
        };
    }
  };

  const COLORS = ['#38bdf8', '#818cf8', '#34d399', '#fbbf24', '#fb923c', '#f472b6', '#a78bfa', '#22d3ee'];

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-2 mb-1">
          <BarChart3 className="w-5 h-5 text-sky-400" />
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">Analysis</span>
        </div>
        <h1 className="text-3xl font-black text-slate-100 tracking-tight">Exploratory Data Analysis</h1>
        <p className="text-sm text-slate-400 mt-1">Real statistics computed from your dataset</p>
      </div>

      {/* Dataset selector */}
      <div className="animate-fade-in-up stagger-1 flex items-center gap-4">
        <select
          value={selectedDataset}
          onChange={e => setSelectedDataset(e.target.value)}
          className="bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:border-sky-500/50 transition-colors"
        >
          <option value="">Select dataset...</option>
          {datasets.map(d => (
            <option key={d.id} value={d.id}>{d.original_filename}</option>
          ))}
        </select>
        <button onClick={runEda} disabled={!selectedDataset || loading}
          className="px-5 py-2.5 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white rounded-xl text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-sky-500/20 transition-all">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
          {loading ? 'Analyzing...' : 'Run EDA'}
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <div key={i} className="skeleton skeleton-card" />)}
          </div>
          <div className="skeleton h-64 rounded-xl" />
        </div>
      )}

      {error && (
        <div className="animate-fade-in p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" /> {error}
        </div>
      )}

      {eda && !loading && (
        <div className="space-y-6">
          {/* Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Rows', value: eda.shape?.rows?.toLocaleString(), color: 'slate' },
              { label: 'Columns', value: eda.shape?.columns, color: 'slate' },
              { label: 'Numerical', value: eda.numerical_stats?.length || 0, color: 'sky' },
              { label: 'Categorical', value: eda.categorical_stats?.length || 0, color: 'purple' },
            ].map((card, idx) => (
              <div key={card.label} className={`animate-fade-in-up stagger-${idx + 1} glass-card border border-slate-800/50 rounded-xl p-4`}>
                <p className="text-xs text-slate-400 uppercase font-semibold">{card.label}</p>
                <p className={`text-2xl font-bold mt-1 ${card.color === 'sky' ? 'text-sky-400' : card.color === 'purple' ? 'text-purple-400' : 'text-slate-100'}`}>{card.value}</p>
              </div>
            ))}
          </div>

          {/* Auto-Insights Card Feed */}
          {insights.length > 0 && (
            <div className="animate-fade-in-up glass-card border border-sky-500/20 rounded-2xl p-6 relative overflow-hidden bg-gradient-to-b from-slate-900/90 to-slate-950/90">
              <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />
              
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-sky-400 animate-pulse" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                      Auto-Insights Engine
                      <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 font-semibold border border-sky-500/30">
                        {insights.length} Findings
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400">Deterministic quality rules & statistical recommendations</p>
                  </div>
                </div>

                <button
                  onClick={() => navigate('/cleaning')}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-xs font-semibold text-sky-400 border border-slate-700/50 flex items-center gap-1.5 transition-all shadow-sm"
                >
                  Go to Cleaning Pipeline <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 mt-2">
                {insights.map((ins: any) => {
                  const style = getSeverityStyle(ins.severity);
                  return (
                    <div
                      key={ins.id || ins.message}
                      className={`p-4 rounded-xl border transition-all hover:scale-[1.01] flex flex-col justify-between ${style.bg}`}
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            {style.icon}
                            {ins.column_name && (
                              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-md bg-slate-900/60 text-slate-200 border border-slate-700/50">
                                {ins.column_name}
                              </span>
                            )}
                            <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">
                              {ins.insight_type?.replace('_', ' ')}
                            </span>
                          </div>
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${style.badge}`}>
                            {ins.severity}
                          </span>
                        </div>

                        <p className="text-sm font-medium text-slate-200 leading-snug">
                          {ins.message}
                        </p>

                        {ins.suggested_action && (
                          <div className="mt-2.5 p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs text-slate-300 flex items-start gap-2">
                            <span className="text-sky-400 font-bold shrink-0">💡 Fix:</span>
                            <span className="text-slate-300">{ins.suggested_action}</span>
                          </div>
                        )}
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-slate-800/40 flex justify-end">
                        <button
                          onClick={() => navigate('/cleaning')}
                          className="text-xs text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1 transition-colors"
                        >
                          Apply in Cleaning <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Observations */}
          {eda.observations?.length > 0 && (
            <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-3">Key Observations</h3>
              <div className="space-y-2">
                {eda.observations.map((obs: any, i: number) => (
                  <div key={i} className={`p-3 rounded-xl text-sm flex items-start gap-2 ${
                    obs.type === 'critical' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                    obs.type === 'warning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                  }`}>
                    <span className="shrink-0 mt-0.5">{obs.type === 'critical' ? <ShieldAlert className="w-4 h-4 text-rose-500" /> : obs.type === 'warning' ? <AlertTriangle className="w-4 h-4 text-amber-500" /> : <AlertCircle className="w-4 h-4 text-blue-500" />}</span>
                    <span>{obs.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Numerical Stats Table */}
          {eda.numerical_stats?.length > 0 && (
            <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5 overflow-x-auto">
              <h3 className="text-sm font-bold text-slate-200 mb-3">Numerical Statistics</h3>
              <div className="rounded-xl border border-slate-800/50 overflow-hidden">
                <table className="w-full text-sm text-left text-slate-300">
                  <thead className="text-xs text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800/50">
                    <tr>
                      {['Column', 'Mean', 'Median', 'Std', 'Min', 'Max', 'Q1', 'Q3', 'Missing'].map(h => (
                        <th key={h} className="px-4 py-3 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {eda.numerical_stats.map((s: any) => (
                      <tr key={s.column} className="hover:bg-slate-800/20 transition-colors">
                        <td className="px-4 py-2.5 font-medium text-slate-200">{s.column}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.mean}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.median}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.std}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.min}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.max}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.q1}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.q3}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{s.missing_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Distribution Charts */}
          {eda.distributions && Object.keys(eda.distributions).length > 0 && (
            <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-4">Distributions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {Object.entries(eda.distributions).slice(0, 6).map(([col, data]: [string, any]) => (
                  <div key={col} className="bg-slate-900/40 rounded-xl p-4 border border-slate-800/30">
                    <p className="text-xs font-semibold text-slate-300 mb-2">{col}</p>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={
                        data.type === 'histogram'
                          ? data.counts.map((c: number, i: number) => ({
                              bin: `${data.bins[i]?.toFixed(1)}`,
                              count: c,
                            }))
                          : data.labels.map((l: string, i: number) => ({
                              bin: l.length > 12 ? l.slice(0, 12) + '…' : l,
                              count: data.counts[i],
                            }))
                      }>
                        <XAxis dataKey="bin" tick={{ fontSize: 9, fill: '#94a3b8' }} interval="preserveStartEnd" />
                        <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} />
                        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', fontSize: '12px' }} />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {(data.type === 'histogram' ? data.counts : data.labels).map((_: any, i: number) => (
                            <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Correlation Matrix */}
          {eda.correlation?.columns?.length > 1 && (
            <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5 overflow-x-auto">
              <h3 className="text-sm font-bold text-slate-200 mb-3">Correlation Matrix</h3>
              <div className="inline-block">
                <table className="text-xs">
                  <thead>
                    <tr>
                      <th className="p-2"></th>
                      {eda.correlation.columns.map((c: string) => (
                        <th key={c} className="p-2 text-slate-400 font-medium max-w-[80px] truncate">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {eda.correlation.columns.map((row: string) => (
                      <tr key={row}>
                        <td className="p-2 text-slate-400 font-medium">{row}</td>
                        {eda.correlation.columns.map((col: string) => {
                          const cell = eda.correlation.matrix.find((m: any) => m.x === row && m.y === col);
                          const val = cell?.value ?? 0;
                          const intensity = Math.abs(val);
                          const bg = val > 0
                            ? `rgba(56, 189, 248, ${intensity * 0.7})`
                            : `rgba(248, 113, 113, ${intensity * 0.7})`;
                          return (
                            <td key={`${row}-${col}`} className="p-2 text-center font-mono rounded"
                              style={{ backgroundColor: bg, color: intensity > 0.5 ? '#fff' : '#94a3b8' }}>
                              {val.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Categorical Stats */}
          {eda.categorical_stats?.length > 0 && (
            <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-3">Categorical Columns</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {eda.categorical_stats.map((s: any) => (
                  <div key={s.column} className="bg-slate-900/40 rounded-xl p-4 border border-slate-800/30">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-200">{s.column}</span>
                      <span className="text-xs text-slate-500 px-2 py-0.5 rounded-lg bg-slate-800/60">{s.unique} unique</span>
                    </div>
                    {s.top_categories?.slice(0, 5).map((cat: any) => (
                      <div key={cat.value} className="flex items-center justify-between py-1.5">
                        <span className="text-xs text-slate-400 truncate max-w-[150px]">{cat.value}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-slate-800/60 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-sky-500 to-blue-500 rounded-full transition-all duration-700" style={{ width: `${cat.percentage}%` }} />
                          </div>
                          <span className="text-xs text-slate-500 font-mono w-12 text-right">{cat.percentage}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!eda && !loading && (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mx-auto">
            <BarChart3 className="w-8 h-8 text-sky-400/60" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Analysis Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">Select a dataset and click "Run EDA" to generate real statistics</p>
          <div className="flex items-center justify-center gap-2 text-sky-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Choose a dataset to begin</span>
          </div>
        </div>
      )}
    </div>
  );
};
