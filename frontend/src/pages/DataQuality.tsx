import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, AlertTriangle, CheckCircle2, Zap, RefreshCw,
  Database, Sparkles, Filter, Loader2, BarChart2, ShieldAlert
} from 'lucide-react';
import { apiService } from '../services/api';
import { useDatasets } from '../hooks/useDatasets';

export const DataQuality: React.FC = () => {
  const { datasets, loading: loadingDatasets } = useDatasets();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [targetColumn, setTargetColumn] = useState<string>('');
  const [columns, setColumns] = useState<string[]>([]);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [remediationResult, setRemediationResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'leakage' | 'consistency' | 'outliers' | 'missingness' | 'validity'>('overview');

  // Remediation toggles
  const [dropLeakage, setDropLeakage] = useState(true);
  const [removeDups, setRemoveDups] = useState(true);
  const [imputeMiss, setImputeMiss] = useState(true);
  const [standardizeFuzzy, setStandardizeFuzzy] = useState(true);

  // Set initial selected dataset
  useEffect(() => {
    if (datasets.length > 0 && !selectedDatasetId) {
      setSelectedDatasetId(datasets[0].id);
      if (datasets[0].target_column) {
        setTargetColumn(datasets[0].target_column);
      }
    }
  }, [datasets, selectedDatasetId]);

  // Load preview to get columns
  useEffect(() => {
    if (selectedDatasetId) {
      apiService.getDatasetPreview(selectedDatasetId, 5).then(res => {
        setColumns(res.columns || []);
      }).catch(() => setColumns([]));

      fetchReport(selectedDatasetId, targetColumn);
    }
  }, [selectedDatasetId]);

  const fetchReport = async (datasetId: string, target?: string) => {
    try {
      setLoading(true);
      setRemediationResult(null);
      const res = await apiService.getDataQuality(datasetId, target || undefined);
      setReport(res);
    } catch (err) {
      console.error('Failed to load quality report', err);
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAssessment = () => {
    if (!selectedDatasetId) return;
    setLoading(true);
    setRemediationResult(null);
    apiService.assessDataQuality(selectedDatasetId, targetColumn || undefined)
      .then(res => setReport(res))
      .catch(err => alert(err?.response?.data?.detail || 'Assessment failed'))
      .finally(() => setLoading(false));
  };

  const handleExecuteRemediation = async () => {
    if (!selectedDatasetId || !report) return;
    try {
      setRemediating(true);
      const highLeaks = report?.dimensions?.leakage_risk?.high_risk_columns || [];
      const dropCols = dropLeakage ? highLeaks : [];

      const res = await apiService.remediateDataQuality(selectedDatasetId, {
        drop_columns: dropCols,
        remove_duplicates: removeDups,
        impute_missing: imputeMiss,
        standardize_fuzzy: standardizeFuzzy,
      });

      setRemediationResult(res);
      // Refresh report
      await fetchReport(selectedDatasetId, targetColumn);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Remediation failed');
    } finally {
      setRemediating(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (score >= 70) return 'text-blue-700 bg-blue-50 border-blue-200';
    if (score >= 50) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-rose-700 bg-rose-50 border-rose-200';
  };

  const getScoreRating = (score: number) => {
    if (score >= 85) return 'Production Ready';
    if (score >= 70) return 'Good Quality';
    if (score >= 50) return 'Fair (Remediation Recommended)';
    return 'Critical Quality Issues';
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <ShieldCheck className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Data Quality Engine v2
            </h1>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            Detect target leakage, fuzzy categorical inconsistencies, multi-strategy outliers, and missingness patterns.
          </p>
        </div>

        {/* Dataset & Target Controls */}
        <div className="flex flex-wrap items-center gap-3 bg-white p-2 rounded-2xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-slate-400 ml-2" />
            <select
              value={selectedDatasetId}
              onChange={e => setSelectedDatasetId(e.target.value)}
              disabled={loadingDatasets}
              className="py-1.5 px-2 text-xs font-semibold rounded-xl border-none bg-slate-50 focus:bg-white"
            >
              {datasets.map(d => (
                <option key={d.id} value={d.id}>
                  {d.original_filename} (v{d.version || 1})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={targetColumn}
              onChange={e => setTargetColumn(e.target.value)}
              className="py-1.5 px-2 text-xs font-semibold rounded-xl border-none bg-slate-50 focus:bg-white"
            >
              <option value="">No Target (General Assessment)</option>
              {columns.map(c => (
                <option key={c} value={c}>Target: {c}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRunAssessment}
            disabled={loading || !selectedDatasetId}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-all"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Re-Assess
          </button>
        </div>
      </div>

      {/* Remediation Success Toast */}
      {remediationResult && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-start gap-3 shadow-sm animate-fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold text-emerald-950">
              Quality Remediation Applied Successfully! Created Dataset Version v{remediationResult.new_version}
            </p>
            <p className="text-emerald-700">
              Changes: {remediationResult.changes_applied.join(' • ')}
            </p>
            <p className="font-mono text-[11px] text-emerald-600">
              New Quality Score: <strong>{remediationResult.new_overall_score}/100</strong>
            </p>
          </div>
        </div>
      )}

      {loading && !report ? (
        <div className="space-y-6">
          <div className="h-44 rounded-3xl skeleton" />
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-28 rounded-2xl skeleton" />)}
          </div>
        </div>
      ) : !report ? (
        <div className="glass-card text-center py-20 rounded-3xl border border-slate-200 shadow-sm">
          <ShieldAlert className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No Assessment Available</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Select a dataset above and click Re-Assess to run the Data Quality Engine.
          </p>
          <button
            onClick={handleRunAssessment}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold"
          >
            Run Quality Assessment
          </button>
        </div>
      ) : (
        <>
          {/* Hero Score Banner */}
          <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200/90 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <div className={`w-24 h-24 rounded-3xl border flex flex-col items-center justify-center shrink-0 shadow-sm ${getScoreColor(report.overall_score)}`}>
                  <span className="text-3xl font-extrabold tracking-tight">
                    {report.overall_score}
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider mt-0.5">/ 100</span>
                </div>

                <div>
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border ${getScoreColor(report.overall_score)}`}>
                    {getScoreRating(report.overall_score)}
                  </span>
                  <h2 className="text-xl font-bold text-slate-900 mt-2">
                    Overall Data Quality Health
                  </h2>
                  <p className="text-xs text-slate-500 mt-1 max-w-md">
                    Weighted evaluation of completeness, validity, uniqueness, consistency, and target leakage safety.
                  </p>
                </div>
              </div>

              {/* Actionable Remediation Box */}
              <div className="bg-slate-50/80 p-5 rounded-2xl border border-slate-200/80 max-w-md w-full space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                    Automated Remediation Plan
                  </h4>
                  <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                    {report.recommendations?.length || 0} Actions
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600">
                  {report.dimensions?.leakage_risk?.high_risk_columns?.length > 0 && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={dropLeakage}
                        onChange={e => setDropLeakage(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span>Drop {report.dimensions.leakage_risk.high_risk_columns.length} target leakage feature(s)</span>
                    </label>
                  )}

                  {report.dimensions?.uniqueness?.duplicate_rows > 0 && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={removeDups}
                        onChange={e => setRemoveDups(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span>Remove {report.dimensions.uniqueness.duplicate_rows} duplicate row(s)</span>
                    </label>
                  )}

                  {report.dimensions?.completeness?.total_missing > 0 && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={imputeMiss}
                        onChange={e => setImputeMiss(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span>Impute missing values in {report.dimensions.completeness.columns_with_missing?.length || 0} column(s)</span>
                    </label>
                  )}

                  {report.dimensions?.consistency?.inconsistent_categories > 0 && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={standardizeFuzzy}
                        onChange={e => setStandardizeFuzzy(e.target.checked)}
                        className="rounded text-blue-600"
                      />
                      <span>Standardize {report.dimensions.consistency.inconsistent_categories} fuzzy category cluster(s)</span>
                    </label>
                  )}
                </div>

                <button
                  onClick={handleExecuteRemediation}
                  disabled={remediating}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition-all"
                >
                  {remediating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                  Execute Automated Remediation
                </button>
              </div>
            </div>

            {/* 5 Dimensions Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-6 pt-6 border-t border-slate-100">
              <div className="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/60">
                <p className="text-[11px] text-slate-500 font-semibold">Completeness</p>
                <p className="text-xl font-bold text-slate-900 mt-1">{report.completeness_score}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{report.dimensions?.completeness?.missing_percentage}% missing</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/60">
                <p className="text-[11px] text-slate-500 font-semibold">Validity</p>
                <p className="text-xl font-bold text-slate-900 mt-1">{report.validity_score}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{report.dimensions?.validity?.semantic_violations_count || 0} violations</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/60">
                <p className="text-[11px] text-slate-500 font-semibold">Uniqueness</p>
                <p className="text-xl font-bold text-slate-900 mt-1">{report.uniqueness_score}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{report.dimensions?.uniqueness?.duplicate_rows || 0} duplicates</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/60">
                <p className="text-[11px] text-slate-500 font-semibold">Consistency</p>
                <p className="text-xl font-bold text-slate-900 mt-1">{report.consistency_score}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{report.dimensions?.consistency?.inconsistent_categories || 0} fuzzy variants</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/60 col-span-2 sm:col-span-1">
                <p className="text-[11px] text-slate-500 font-semibold">Leakage Safety</p>
                <p className="text-xl font-bold text-slate-900 mt-1">{report.leakage_score}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {report.dimensions?.leakage_risk?.high_risk_columns?.length || 0} leak features
                </p>
              </div>
            </div>
          </div>

          {/* Deep Dive Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-200 overflow-x-auto pb-px">
            {[
              { id: 'overview', label: 'Actionable Recommendations', icon: Sparkles },
              { id: 'leakage', label: `Target Leakage (${report.dimensions?.leakage_risk?.high_risk_columns?.length || 0})`, icon: ShieldAlert },
              { id: 'consistency', label: `Fuzzy Inconsistencies (${report.dimensions?.consistency?.inconsistent_categories || 0})`, icon: CheckCircle2 },
              { id: 'outliers', label: `Outliers (${report.dimensions?.outliers?.columns?.length || 0})`, icon: BarChart2 },
              { id: 'missingness', label: `Missingness (${report.dimensions?.completeness?.columns_with_missing?.length || 0})`, icon: Filter },
              { id: 'validity', label: `Validity Issues (${report.dimensions?.validity?.issues?.length || 0})`, icon: AlertTriangle },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
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

          {/* Tab 1: Recommendations */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">Recommended Quality Improvements</h3>
              {report.recommendations?.length === 0 ? (
                <div className="p-8 rounded-3xl bg-emerald-50 text-emerald-800 text-center text-sm font-medium">
                  🎉 No critical data quality defects detected! Your dataset is ready for high-fidelity modeling.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {report.recommendations.map((rec: any, idx: number) => (
                    <div key={idx} className="glass-card p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-2">
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                          rec.priority === 'HIGH' ? 'bg-rose-50 text-rose-700 border border-rose-100' : 'bg-amber-50 text-amber-700 border border-amber-100'
                        }`}>
                          {rec.priority} Priority
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 capitalize">{rec.category}</span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">{rec.action}</h4>
                      <p className="text-xs text-slate-600">{rec.detail}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Target Leakage */}
          {activeTab === 'leakage' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Target Leakage Diagnostics</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Target Column: <strong>{targetColumn || 'Auto-detected / none'}</strong>
                  </p>
                </div>
              </div>

              {report.dimensions?.leakage_risk?.details?.length === 0 ? (
                <div className="p-8 rounded-3xl bg-emerald-50 text-emerald-800 text-center text-sm font-medium">
                  No features exhibit suspicious target correlation. Leakage risk is low.
                </div>
              ) : (
                <div className="space-y-3">
                  {report.dimensions.leakage_risk.details.map((leak: any, idx: number) => (
                    <div key={idx} className="p-4 rounded-2xl border border-rose-200 bg-rose-50/60 flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{leak.column}</span>
                          <span className="px-2 py-0.5 rounded-full bg-rose-600 text-white text-[10px] font-bold uppercase">
                            {leak.risk_level} Risk Leak
                          </span>
                        </div>
                        <p className="text-xs text-rose-700 mt-1">{leak.reason}</p>
                        <span className="text-[10px] text-slate-400 font-mono mt-2 block">
                          Method: {leak.detection_method} • Score: {leak.association_score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Consistency */}
          {activeTab === 'consistency' && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">Fuzzy Categorical Variant Clusters</h3>
              {report.dimensions?.consistency?.details?.length === 0 ? (
                <div className="p-8 rounded-3xl bg-emerald-50 text-emerald-800 text-center text-sm font-medium">
                  All categorical variables follow clean, consistent naming conventions.
                </div>
              ) : (
                <div className="space-y-4">
                  {report.dimensions.consistency.details.map((colItem: any, idx: number) => (
                    <div key={idx} className="glass-card p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-bold text-slate-900">Column: {colItem.column}</h4>
                        <span className="text-xs text-slate-400">{colItem.unique_values_count} unique values</span>
                      </div>

                      <div className="space-y-2">
                        {colItem.inconsistency_clusters.map((cluster: any, cIdx: number) => (
                          <div key={cIdx} className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-slate-500">Detected variants:</span>
                              <div className="flex flex-wrap gap-1">
                                {cluster.variants.map((v: string, vIdx: number) => (
                                  <span key={vIdx} className="px-2 py-0.5 rounded-md bg-white border border-slate-200 font-mono text-[11px]">
                                    "{v}"
                                  </span>
                                ))}
                              </div>
                            </div>
                            <span className="text-blue-600 font-semibold flex items-center gap-1">
                              Canonical: <strong>"{cluster.canonical_suggestion}"</strong>
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Outliers */}
          {activeTab === 'outliers' && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">Multi-Strategy Outlier Breakdown</h3>
              {report.dimensions?.outliers?.columns?.length === 0 ? (
                <div className="p-8 rounded-3xl bg-emerald-50 text-emerald-800 text-center text-sm font-medium">
                  No extreme numerical outliers detected outside IQR / Z-score thresholds.
                </div>
              ) : (
                <div className="glass-card rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 uppercase font-bold">
                      <tr>
                        <th className="px-4 py-3">Column</th>
                        <th className="px-4 py-3">IQR Outliers</th>
                        <th className="px-4 py-3">Z-Score Outliers</th>
                        <th className="px-4 py-3">% Outliers</th>
                        <th className="px-4 py-3">Normal Bounds</th>
                        <th className="px-4 py-3">Observed Range</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {report.dimensions.outliers.columns.map((col: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="px-4 py-3 font-semibold text-slate-900">{col.column}</td>
                          <td className="px-4 py-3 font-mono">{col.iqr_outliers}</td>
                          <td className="px-4 py-3 font-mono">{col.zscore_outliers}</td>
                          <td className="px-4 py-3 font-bold text-amber-600">{col.percentage}%</td>
                          <td className="px-4 py-3 font-mono text-slate-500">[{col.lower_bound}, {col.upper_bound}]</td>
                          <td className="px-4 py-3 font-mono text-slate-500">[{col.min}, {col.max}]</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab 5: Missingness */}
          {activeTab === 'missingness' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900">Missingness Patterns</h3>
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                  Pattern: {report.dimensions?.completeness?.pattern}
                </span>
              </div>

              {report.dimensions?.completeness?.columns_with_missing?.length === 0 ? (
                <div className="p-8 rounded-3xl bg-emerald-50 text-emerald-800 text-center text-sm font-medium">
                  Zero missing values across all columns! Dataset completeness is 100%.
                </div>
              ) : (
                <div className="glass-card rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 uppercase font-bold">
                      <tr>
                        <th className="px-4 py-3">Column Name</th>
                        <th className="px-4 py-3">Missing Cells</th>
                        <th className="px-4 py-3">Missing Percentage</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {report.dimensions.completeness.columns_with_missing.map((col: any, idx: number) => (
                        <tr key={idx}>
                          <td className="px-4 py-3 font-semibold text-slate-900">{col.column}</td>
                          <td className="px-4 py-3 font-mono">{col.count}</td>
                          <td className="px-4 py-3 font-bold text-rose-600">{col.percentage}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab 6: Validity */}
          {activeTab === 'validity' && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">Semantic & Range Validity Violations</h3>
              {report.dimensions?.validity?.issues?.length === 0 ? (
                <div className="p-8 rounded-3xl bg-emerald-50 text-emerald-800 text-center text-sm font-medium">
                  No invalid domain values or sentinel placeholders detected.
                </div>
              ) : (
                <div className="space-y-3">
                  {report.dimensions.validity.issues.map((iss: any, idx: number) => (
                    <div key={idx} className="p-4 rounded-2xl border border-amber-200 bg-amber-50/60 flex items-center justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900">{iss.column}</span>
                          <span className="px-2 py-0.5 rounded-full bg-amber-600 text-white text-[10px] font-bold">
                            {iss.issue_type}
                          </span>
                        </div>
                        <p className="text-slate-600 mt-1">{iss.description}</p>
                      </div>
                      <span className="font-bold text-amber-900 text-sm">{iss.count} rows</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};
