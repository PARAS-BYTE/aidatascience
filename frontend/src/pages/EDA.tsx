import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import {
  BarChart3, AlertCircle, Loader2, Sparkles,
  AlertTriangle, CheckCircle2, ShieldAlert, ArrowUpRight,
  Scale, FileText, Download, Play
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export const EDA: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [targetColumn, setTargetColumn] = useState<string>('');
  const [eda, setEda] = useState<any>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Phase 3 States
  const [activeSection, setActiveSection] = useState<'visuals' | 'hypothesis' | 'report'>('visuals');
  const [statsData, setStatsData] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [reportData, setReportData] = useState<any>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  // Pairwise test playground
  const [colA, setColA] = useState<string>('');
  const [colB, setColB] = useState<string>('');
  const [pairwiseResult, setPairwiseResult] = useState<any>(null);
  const [runningPairwise, setRunningPairwise] = useState(false);

  // Smart chart recommendation
  const [chartRec, setChartRec] = useState<any>(null);

  useEffect(() => {
    apiService.getDatasets().then(r => {
      setDatasets(r.items || []);
      if (r.items?.length > 0) {
        setSelectedDataset(r.items[0].id);
        if (r.items[0].target_column) setTargetColumn(r.items[0].target_column);
      }
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

  const loadStatisticalTests = async (datasetId: string, target?: string) => {
    try {
      setLoadingStats(true);
      const res = await apiService.getStatisticalTests(datasetId, target || undefined);
      setStatsData(res);
    } catch (e) {
      console.error("Failed to load statistical tests", e);
    } finally {
      setLoadingStats(false);
    }
  };

  const loadAutoEdaReport = async (datasetId: string, target?: string) => {
    try {
      setLoadingReport(true);
      const res = await apiService.getAutoEdaReport(datasetId, target || undefined);
      setReportData(res);
    } catch (e) {
      console.error("Failed to load auto-eda report", e);
    } finally {
      setLoadingReport(false);
    }
  };

  useEffect(() => {
    if (selectedDataset) {
      loadInsights(selectedDataset);
      loadStatisticalTests(selectedDataset, targetColumn);
      setPairwiseResult(null);
      setChartRec(null);
    }
  }, [selectedDataset]);

  const runEda = async () => {
    if (!selectedDataset) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.runEda(selectedDataset, targetColumn || undefined);
      setEda(result);
      await loadInsights(selectedDataset);
      await loadStatisticalTests(selectedDataset, targetColumn);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'EDA failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRunPairwiseTest = async () => {
    if (!selectedDataset || !colA || !colB) return;
    try {
      setRunningPairwise(true);
      const [testRes, recRes] = await Promise.all([
        apiService.getStatisticalTests(selectedDataset, undefined, colA, colB),
        apiService.getChartRecommendation(selectedDataset, colA, colB),
      ]);
      setPairwiseResult(testRes);
      setChartRec(recRes);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Pairwise test failed.');
    } finally {
      setRunningPairwise(false);
    }
  };

  const downloadMarkdownReport = () => {
    if (!reportData?.markdown_report) return;
    const blob = new Blob([reportData.markdown_report], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `auto_eda_report_${selectedDataset}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return {
          bg: 'bg-rose-50 border-rose-200 text-rose-800',
          badge: 'bg-rose-100 text-rose-700 border border-rose-200',
          icon: <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
        };
      case 'high':
        return {
          bg: 'bg-amber-50 border-amber-200 text-amber-800',
          badge: 'bg-amber-100 text-amber-700 border border-amber-200',
          icon: <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
        };
      case 'medium':
        return {
          bg: 'bg-blue-50 border-blue-200 text-blue-800',
          badge: 'bg-blue-100 text-blue-700 border border-blue-200',
          icon: <AlertCircle className="w-4 h-4 text-blue-600 shrink-0" />
        };
      default:
        return {
          bg: 'bg-emerald-50 border-emerald-200 text-emerald-800',
          badge: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
        };
    }
  };

  const allColumns = eda?.numerical_stats?.map((s: any) => s.column)
    .concat(eda?.categorical_stats?.map((s: any) => s.column) || []) || [];

  return (
    <div className="space-y-6 animate-fade-in max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <BarChart3 className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Exploratory Data Analysis & Statistics
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Deterministic descriptive statistics, inferential hypothesis tests, and auto-generated insights.
          </p>
        </div>

        {/* Dataset selector & Run CTA */}
        <div className="flex flex-wrap items-center gap-3 bg-white p-2 rounded-2xl border border-slate-200/80 shadow-sm">
          <select
            value={selectedDataset}
            onChange={e => setSelectedDataset(e.target.value)}
            className="py-1.5 px-3 text-xs font-semibold rounded-xl border-none bg-slate-50 focus:bg-white"
          >
            {datasets.map(d => (
              <option key={d.id} value={d.id}>
                {d.original_filename} (v{d.version || 1})
              </option>
            ))}
          </select>

          <button
            onClick={runEda}
            disabled={loading || !selectedDataset}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-all"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            Compute EDA
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 overflow-x-auto pb-px">
        {[
          { id: 'visuals', label: 'Visual Distributions & Correlations', icon: BarChart3 },
          { id: 'hypothesis', label: 'Hypothesis Testing & Inference', icon: Scale },
          { id: 'report', label: 'Auto-EDA Executive Report', icon: FileText },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeSection === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveSection(tab.id as any);
                if (tab.id === 'report' && !reportData) {
                  loadAutoEdaReport(selectedDataset, targetColumn);
                }
              }}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 whitespace-nowrap transition-colors ${
                isActive
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: VISUAL DISTRIBUTIONS & CORRELATIONS */}
      {activeSection === 'visuals' && (
        <div className="space-y-6">
          {/* Automated Insights Strip */}
          {insights.length > 0 && (
            <div className="glass-card border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  <h3 className="text-sm font-bold text-slate-900">Key Automated Insights</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">{insights.length} discovered</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {insights.map((insight: any) => {
                  const style = getSeverityStyle(insight.severity || 'low');
                  return (
                    <div
                      key={insight.id}
                      onClick={() => insight.action_url && navigate(insight.action_url)}
                      className={`p-4 rounded-xl border ${style.bg} ${insight.action_url ? 'cursor-pointer hover:shadow-sm transition-all' : ''}`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          {style.icon}
                          <span className="text-xs font-bold text-slate-900">{insight.title}</span>
                        </div>
                        {insight.action_url && <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{insight.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {eda && (
            <div className="space-y-6">
              {/* Numerical Stats Table */}
              {eda.numerical_stats?.length > 0 && (
                <div className="glass-card border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 overflow-x-auto">
                  <h3 className="text-sm font-bold text-slate-900">Numerical Column Statistics</h3>
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-bold">
                      <tr>
                        <th className="px-3 py-2.5">Column</th>
                        <th className="px-3 py-2.5">Count</th>
                        <th className="px-3 py-2.5">Mean</th>
                        <th className="px-3 py-2.5">Median</th>
                        <th className="px-3 py-2.5">Std</th>
                        <th className="px-3 py-2.5">Min</th>
                        <th className="px-3 py-2.5">Max</th>
                        <th className="px-3 py-2.5">Skew</th>
                        <th className="px-3 py-2.5">Missing</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {eda.numerical_stats.map((s: any) => (
                        <tr key={s.column} className="hover:bg-slate-50/60">
                          <td className="px-3 py-2.5 font-bold text-slate-900 font-sans">{s.column}</td>
                          <td className="px-3 py-2.5">{s.count}</td>
                          <td className="px-3 py-2.5">{s.mean}</td>
                          <td className="px-3 py-2.5">{s.median}</td>
                          <td className="px-3 py-2.5">{s.std}</td>
                          <td className="px-3 py-2.5">{s.min}</td>
                          <td className="px-3 py-2.5">{s.max}</td>
                          <td className={`px-3 py-2.5 ${Math.abs(s.skew) > 1 ? 'text-amber-600 font-bold' : ''}`}>{s.skew}</td>
                          <td className={`px-3 py-2.5 ${s.missing > 0 ? 'text-rose-600 font-bold' : ''}`}>{s.missing_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Distributions Grid */}
              {eda.distributions && Object.keys(eda.distributions).length > 0 && (
                <div className="glass-card border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                  <h3 className="text-sm font-bold text-slate-900">Feature Distributions</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Object.entries(eda.distributions).slice(0, 6).map(([col, data]: [string, any]) => (
                      <div key={col} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                        <span className="text-xs font-bold text-slate-900">{col}</span>
                        <ResponsiveContainer width="100%" height={160}>
                          <BarChart data={data.bins ? data.bins.map((b: string, i: number) => ({ bin: b, count: data.counts[i] })) : []}>
                            <XAxis dataKey="bin" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
                            <YAxis tick={{ fontSize: 9 }} />
                            <Tooltip contentStyle={{ borderRadius: '8px', fontSize: '11px' }} />
                            <Bar dataKey="count" fill="#2563eb" radius={[3, 3, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Correlation Matrix */}
              {eda.correlation?.columns?.length > 1 && (
                <div className="glass-card border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 overflow-x-auto">
                  <h3 className="text-sm font-bold text-slate-900">Correlation Matrix</h3>
                  <div className="inline-block min-w-full">
                    <table className="text-xs">
                      <thead>
                        <tr>
                          <th className="p-2"></th>
                          {eda.correlation.columns.map((c: string) => (
                            <th key={c} className="p-2 text-slate-500 font-semibold max-w-[100px] truncate">{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {eda.correlation.columns.map((row: string) => (
                          <tr key={row}>
                            <td className="p-2 text-slate-700 font-semibold">{row}</td>
                            {eda.correlation.columns.map((col: string) => {
                              const cell = eda.correlation.matrix.find((m: any) => m.x === row && m.y === col);
                              const val = cell?.value ?? 0;
                              const intensity = Math.abs(val);
                              const bg = val > 0 ? `rgba(37, 99, 235, ${intensity * 0.4})` : `rgba(225, 29, 72, ${intensity * 0.4})`;
                              return (
                                <td key={`${row}-${col}`} className="p-2 text-center font-mono rounded" style={{ backgroundColor: bg }}>
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
            </div>
          )}

          {!eda && !loading && (
            <div className="glass-card border border-slate-200 rounded-2xl p-16 text-center space-y-3">
              <BarChart3 className="w-12 h-12 text-slate-300 mx-auto" />
              <h3 className="text-lg font-bold text-slate-800">No EDA Computed Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Click "Compute EDA" above to calculate descriptive stats, correlations, and distribution frequencies.
              </p>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: HYPOTHESIS TESTING & STATISTICAL INFERENCE */}
      {activeSection === 'hypothesis' && (
        <div className="space-y-6">
          {/* Target Hypothesis Battery */}
          <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200 shadow-sm space-y-5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-[11px] font-bold text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  Inferential Statistics
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  Target Hypothesis Battery
                </h3>
                <p className="text-xs text-slate-500">
                  Automated significance testing (t-test, ANOVA, Chi-squared, Pearson/Spearman) against target column.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500">Target:</span>
                <select
                  value={targetColumn}
                  onChange={e => {
                    setTargetColumn(e.target.value);
                    loadStatisticalTests(selectedDataset, e.target.value);
                  }}
                  className="py-1.5 px-3 rounded-xl border border-slate-200 text-xs font-semibold bg-slate-50"
                >
                  <option value="">Default (Last column)</option>
                  {allColumns.map((c: string) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>

            {loadingStats ? (
              <div className="py-12 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                Computing hypothesis tests across all variables...
              </div>
            ) : !statsData?.hypothesis_battery ? (
              <div className="p-8 text-center text-xs text-slate-400">
                No statistical battery data available. Click Compute EDA or select a target.
              </div>
            ) : (
              <div className="space-y-5">
                {/* Executive Narrative */}
                <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-100 text-blue-900 text-xs leading-relaxed">
                  <div className="flex items-center gap-1.5 font-bold mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                    Statistical Significance Summary
                  </div>
                  {statsData.hypothesis_battery.executive_narrative}
                </div>

                {/* Significance Leaderboard Table */}
                <div className="rounded-2xl border border-slate-200 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-bold">
                      <tr>
                        <th className="px-4 py-3">Feature</th>
                        <th className="px-4 py-3">Type</th>
                        <th className="px-4 py-3">Test Applied</th>
                        <th className="px-4 py-3">Statistic</th>
                        <th className="px-4 py-3">p-value</th>
                        <th className="px-4 py-3">Significance</th>
                        <th className="px-4 py-3">Effect Size</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {statsData.hypothesis_battery.tests?.map((test: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50/60 font-sans">
                          <td className="px-4 py-3 font-bold text-slate-900">{test.feature}</td>
                          <td className="px-4 py-3 text-slate-500 text-[11px] capitalize">{test.feature_type}</td>
                          <td className="px-4 py-3 font-mono text-[11px] text-slate-600">{test.test_name}</td>
                          <td className="px-4 py-3 font-mono">{test.statistic !== null ? test.statistic : '—'}</td>
                          <td className="px-4 py-3 font-mono font-bold">
                            {test.p_value !== null ? (test.p_value < 0.001 ? '< 0.001' : test.p_value) : '—'}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              test.is_significant ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500'
                            }`}>
                              {test.is_significant ? 'Significant (p < 0.05)' : 'Not Significant'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-600 font-mono text-[11px]">{test.effect_size}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Interactive Pairwise Hypothesis Playground */}
          <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200 shadow-sm space-y-5">
            <h3 className="text-base font-bold text-slate-900">Pairwise Hypothesis Testing Playground</h3>
            <p className="text-xs text-slate-500">
              Select any two features to run automated hypothesis tests (Welch's t-test, ANOVA, Chi-squared, or Pearson/Spearman) with effect sizes and recommended charts.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <select
                value={colA}
                onChange={e => setColA(e.target.value)}
                className="py-2 px-3 rounded-xl border border-slate-300 text-xs font-semibold"
              >
                <option value="">Select Variable A...</option>
                {allColumns.map((c: string) => (
                  <option key={c} value={c}>Variable A: {c}</option>
                ))}
              </select>

              <select
                value={colB}
                onChange={e => setColB(e.target.value)}
                className="py-2 px-3 rounded-xl border border-slate-300 text-xs font-semibold"
              >
                <option value="">Select Variable B...</option>
                {allColumns.map((c: string) => (
                  <option key={c} value={c}>Variable B: {c}</option>
                ))}
              </select>

              <button
                onClick={handleRunPairwiseTest}
                disabled={runningPairwise || !colA || !colB}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm"
              >
                {runningPairwise ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Scale className="w-3.5 h-3.5" />}
                Run Pairwise Test
              </button>
            </div>

            {pairwiseResult && (
              <div className="mt-4 p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 animate-fade-in">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    {pairwiseResult.test_name || 'Statistical Test Result'}
                  </h4>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    pairwiseResult.is_significant ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {pairwiseResult.is_significant ? 'Statistically Significant' : 'No Significant Difference'}
                  </span>
                </div>

                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {pairwiseResult.interpretation}
                </p>

                {chartRec && (
                  <div className="pt-3 border-t border-slate-200 text-xs flex items-start gap-2 text-slate-600">
                    <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-slate-900">Recommended Visualization: </span>
                      <span className="capitalize font-semibold text-blue-700">{chartRec.primary_chart?.replace(/_/g, ' ')}</span>
                      <p className="text-slate-500 text-[11px] mt-0.5">{chartRec.explanation}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Normality Diagnostics Cards */}
          {statsData?.normality_tests?.length > 0 && (
            <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900">Continuous Variable Normality Diagnostics</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {statsData.normality_tests.map((n: any) => (
                  <div key={n.column} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 text-xs">{n.column}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        n.is_normal ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {n.is_normal ? 'Normal' : 'Non-Normal'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-snug">{n.interpretation}</p>
                    <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono pt-1">
                      <span>Skew: {n.skewness}</span>
                      <span>Kurtosis: {n.kurtosis}</span>
                      <span>p: {n.p_value}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AUTO-EDA EXECUTIVE REPORT */}
      {activeSection === 'report' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">Automated EDA Executive Report</h3>
              <p className="text-xs text-slate-500 mt-0.5">Publication-ready synthesis of distributions, correlations, and key predictors.</p>
            </div>

            <button
              onClick={downloadMarkdownReport}
              disabled={!reportData?.markdown_report}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm"
            >
              <Download className="w-3.5 h-3.5" />
              Download Report (.md)
            </button>
          </div>

          {loadingReport ? (
            <div className="py-20 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
              Compiling comprehensive Auto-EDA report...
            </div>
          ) : !reportData ? (
            <div className="glass-card text-center py-16 rounded-3xl border border-slate-200">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-xs text-slate-500">No report generated yet.</p>
            </div>
          ) : (
            <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6">
              <div className="prose prose-sm max-w-none text-slate-800 leading-relaxed font-sans">
                <pre className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-xs font-mono whitespace-pre-wrap text-slate-800">
                  {reportData.markdown_report}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
