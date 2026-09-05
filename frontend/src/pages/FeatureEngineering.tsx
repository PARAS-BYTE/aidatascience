import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, Layers, Sliders, Play, CheckCircle2,
  Table as TableIcon, BarChart2, Activity, ArrowRight, RefreshCw, Cpu
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts';
import { apiService } from '../services/api';

export const FeatureEngineering: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [targetColumn, setTargetColumn] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'transformed' | 'pca' | 'correlations' | 'steps' | 'candidates'>('transformed');

  // Config toggles
  const [enablePca, setEnablePca] = useState(true);
  const [pcaComponents, setPcaComponents] = useState(2);
  const [dropPcaOriginal, setDropPcaOriginal] = useState(false);
  const [enableInteractions, setEnableInteractions] = useState(true);
  const [maxInteractions, setMaxInteractions] = useState(4);
  const [enablePolynomial, setEnablePolynomial] = useState(false);
  const [polynomialDegree, setPolynomialDegree] = useState(2);
  const [enableDateFeatures, setEnableDateFeatures] = useState(true);

  // Result state
  const [result, setResult] = useState<any>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [selectedCandidates, setSelectedCandidates] = useState<Record<string, boolean>>({});

  const fetchCandidates = async () => {
    if (!selectedDatasetId) return;
    setLoadingCandidates(true);
    try {
      const res = await apiService.autoGenerateFeatures(selectedDatasetId, targetColumn || undefined);
      if (res?.candidates) {
        setCandidates(res.candidates);
        setActiveTab('candidates' as any);
      }
    } catch (err) {
      console.error('Failed to generate candidate features:', err);
    } finally {
      setLoadingCandidates(false);
    }
  };

  useEffect(() => {
    apiService.getDatasets().then((r) => {
      const items = r.items || [];
      setDatasets(items);
      if (items.length > 0) {
        setSelectedDatasetId(items[0].id);
        if (items[0].target_column) {
          setTargetColumn(items[0].target_column);
        }
      }
    });
  }, []);

  const runPreview = async (datasetId = selectedDatasetId) => {
    if (!datasetId) return;
    setLoading(true);
    try {
      const data = await apiService.previewFeatureEngineering(datasetId, {
        target: targetColumn || undefined,
        enable_pca: enablePca,
        pca_components: pcaComponents,
        drop_pca_original: dropPcaOriginal,
        enable_interactions: enableInteractions,
        max_interactions: maxInteractions,
        enable_polynomial: enablePolynomial,
        polynomial_degree: polynomialDegree,
        enable_date_features: enableDateFeatures,
        preview_limit: 30,
      });
      setResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDatasetId) {
      runPreview(selectedDatasetId);
    }
  }, [selectedDatasetId]);

  const pcaChartData = result?.pca_report?.loadings?.map((l: any, idx: number) => ({
    component: `PC ${idx + 1}`,
    variance: Math.round(l.explained_variance * 1000) / 10,
  })) || [];

  const correlationChartData = Object.entries(result?.target_correlations || {})
    .slice(0, 10)
    .map(([feature, corr]) => ({
      feature,
      correlation: corr as number,
    }));

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Feature Engineering Studio</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> PCA & Transformations
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Construct interaction terms, compute Principal Component Analysis (PCA), and inspect transformed matrices.
          </p>
        </div>

        {/* Dataset selector */}
        <div className="flex items-center gap-3">
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl px-3.5 py-2 focus:outline-none focus:border-sky-500"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename}
              </option>
            ))}
          </select>

          <button
            onClick={fetchCandidates}
            disabled={loadingCandidates || !selectedDatasetId}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 font-medium text-sm transition-all shadow-lg shadow-amber-500/10 disabled:opacity-50"
          >
            {loadingCandidates ? <RefreshCw className="w-4 h-4 animate-spin text-amber-400" /> : <Sparkles className="w-4 h-4 text-amber-400" />}
            <span>Auto-Generate Ideas</span>
          </button>

          <button
            onClick={() => runPreview()}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium text-sm transition-all shadow-lg shadow-purple-600/20 disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>Apply Transformations</span>
          </button>
        </div>
      </div>

      {/* Configuration Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* PCA Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Layers className="w-4 h-4 text-sky-400" /> PCA Reduction
            </div>
            <input
              type="checkbox"
              checked={enablePca}
              onChange={(e) => setEnablePca(e.target.checked)}
              className="w-4 h-4 rounded text-sky-500 bg-slate-950 border-slate-700 focus:ring-0"
            />
          </div>
          <p className="text-xs text-slate-400">
            Compress numerical features into orthogonal principal components.
          </p>
          {enablePca && (
            <div className="space-y-3 pt-2 border-t border-slate-800/80">
              <div>
                <label className="text-[11px] font-medium text-slate-400 flex justify-between">
                  <span>Components (k):</span>
                  <span className="text-sky-400 font-bold">{pcaComponents}</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={6}
                  value={pcaComponents}
                  onChange={(e) => setPcaComponents(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
                />
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={dropPcaOriginal}
                  onChange={(e) => setDropPcaOriginal(e.target.checked)}
                  className="w-3.5 h-3.5 rounded text-sky-500 bg-slate-950 border-slate-700"
                />
                <span>Drop original numeric cols</span>
              </label>
            </div>
          )}
        </div>

        {/* Interaction Features Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Sliders className="w-4 h-4 text-purple-400" /> Feature Interactions
            </div>
            <input
              type="checkbox"
              checked={enableInteractions}
              onChange={(e) => setEnableInteractions(e.target.checked)}
              className="w-4 h-4 rounded text-purple-500 bg-slate-950 border-slate-700 focus:ring-0"
            />
          </div>
          <p className="text-xs text-slate-400">
            Create multiplicative terms between top correlated numerical columns.
          </p>
          {enableInteractions && (
            <div className="space-y-2 pt-2 border-t border-slate-800/80">
              <label className="text-[11px] font-medium text-slate-400 flex justify-between">
                <span>Max Interactions:</span>
                <span className="text-purple-400 font-bold">{maxInteractions}</span>
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={maxInteractions}
                onChange={(e) => setMaxInteractions(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
            </div>
          )}
        </div>

        {/* Polynomial Features Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Activity className="w-4 h-4 text-emerald-400" /> Non-Linear Polynomials
            </div>
            <input
              type="checkbox"
              checked={enablePolynomial}
              onChange={(e) => setEnablePolynomial(e.target.checked)}
              className="w-4 h-4 rounded text-emerald-500 bg-slate-950 border-slate-700 focus:ring-0"
            />
          </div>
          <p className="text-xs text-slate-400">
            Generate squared non-linear polynomial terms for non-binary features.
          </p>
          {enablePolynomial && (
            <div className="space-y-2 pt-2 border-t border-slate-800/80">
              <label className="text-[11px] font-medium text-slate-400 flex justify-between">
                <span>Degree:</span>
                <span className="text-emerald-400 font-bold">{polynomialDegree}</span>
              </label>
              <select
                value={polynomialDegree}
                onChange={(e) => setPolynomialDegree(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2 py-1.5"
              >
                <option value={2}>Quadratic (Degree 2)</option>
                <option value={3}>Cubic (Degree 3)</option>
              </select>
            </div>
          )}
        </div>

        {/* Temporal Date Features Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Cpu className="w-4 h-4 text-amber-400" /> Date Decompositions
            </div>
            <input
              type="checkbox"
              checked={enableDateFeatures}
              onChange={(e) => setEnableDateFeatures(e.target.checked)}
              className="w-4 h-4 rounded text-amber-500 bg-slate-950 border-slate-700 focus:ring-0"
            />
          </div>
          <p className="text-xs text-slate-400">
            Extract year, month, day, day of week, and quarter from temporal columns.
          </p>
          <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-500">
            Automatically decomposes parsed ISO/date strings into ML features.
          </div>
        </div>
      </div>

      {/* Summary Stats Banner */}
      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">Original Dimensions</p>
            <p className="text-lg font-bold text-slate-100 mt-1">
              {result.original_shape[0]} <span className="text-xs font-normal text-slate-500">rows</span> × {result.original_shape[1]} <span className="text-xs font-normal text-slate-500">cols</span>
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">Transformed Dimensions</p>
            <p className="text-lg font-bold text-purple-400 mt-1">
              {result.transformed_shape[0]} <span className="text-xs font-normal text-slate-500">rows</span> × {result.transformed_shape[1]} <span className="text-xs font-normal text-slate-500">cols</span>
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">New Features Created</p>
            <p className="text-lg font-bold text-emerald-400 mt-1">
              +{result.new_features?.length || 0}
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">PCA Total Variance</p>
            <p className="text-lg font-bold text-sky-400 mt-1">
              {result.pca_report?.applied ? `${Math.round(result.pca_report.total_explained_variance * 100)}%` : 'N/A'}
            </p>
          </div>
        </div>
      )}

      {/* Tabs & Content */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        {/* Tab Headers */}
        <div className="flex border-b border-slate-800 bg-slate-950/50 px-4">
          <button
            onClick={() => setActiveTab('transformed')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'transformed'
                ? 'border-purple-500 text-purple-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <TableIcon className="w-4 h-4" /> Transformed Table Preview
          </button>
          {result?.pca_report?.applied && (
            <button
              onClick={() => setActiveTab('pca')}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all ${
                activeTab === 'pca'
                  ? 'border-sky-500 text-sky-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-4 h-4" /> PCA Scree & Loadings
            </button>
          )}
          {Object.keys(result?.target_correlations || {}).length > 0 && (
            <button
              onClick={() => setActiveTab('correlations')}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all ${
                activeTab === 'correlations'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-4 h-4" /> Target Correlations
            </button>
          )}
          <button
            onClick={() => setActiveTab('steps')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'steps'
                ? 'border-amber-500 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" /> Pipeline Steps ({result?.steps?.length || 0})
          </button>

          {candidates.length > 0 && (
            <button
              onClick={() => setActiveTab('candidates')}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all ${
                activeTab === 'candidates'
                  ? 'border-amber-400 text-amber-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-4 h-4 text-amber-400" /> Auto Ideas ({candidates.length})
            </button>
          )}
        </div>

        {/* Tab Body */}
        <div className="p-6">
          {/* 1. Transformed Table */}
          {activeTab === 'transformed' && result && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Showing first {result.transformed_preview?.length || 0} transformed records:</span>
                <span className="flex items-center gap-1.5 text-purple-400">
                  <span className="w-2 h-2 rounded-full bg-purple-400"></span> Purple headers indicate engineered features
                </span>
              </div>

              <div className="overflow-x-auto max-h-[480px] rounded-xl border border-slate-800">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-950 text-slate-400 sticky top-0 z-10 border-b border-slate-800">
                    <tr>
                      {result.transformed_columns?.map((col: string) => {
                        const isNew = result.new_features?.includes(col);
                        return (
                          <th
                            key={col}
                            className={`p-3 font-semibold whitespace-nowrap ${
                              isNew ? 'bg-purple-950/40 text-purple-300 border-b border-purple-500/30' : ''
                            }`}
                          >
                            <div className="flex items-center gap-1">
                              {col}
                              {isNew && <span className="text-[9px] px-1 py-0.2 rounded bg-purple-500/20 text-purple-400">NEW</span>}
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {result.transformed_preview?.map((row: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                        {result.transformed_columns?.map((col: string) => {
                          const isNew = result.new_features?.includes(col);
                          return (
                            <td
                              key={col}
                              className={`p-3 text-slate-300 whitespace-nowrap ${
                                isNew ? 'bg-purple-950/10 text-purple-200 font-semibold' : ''
                              }`}
                            >
                              {row[col] !== null && row[col] !== undefined ? String(row[col]) : '—'}
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

          {/* 2. PCA Scree & Loadings */}
          {activeTab === 'pca' && result?.pca_report && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">Explained Variance by Component</h3>
                  <div className="h-64 w-full bg-slate-950 p-4 rounded-xl border border-slate-800">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={pcaChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="component" stroke="#64748b" fontSize={11} />
                        <YAxis stroke="#64748b" fontSize={11} unit="%" />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                          formatter={(v: any) => [`${v}%`, 'Variance Explained']}
                        />
                        <Bar dataKey="variance" fill="#0284c7" radius={[4, 4, 0, 0]}>
                          {pcaChartData.map((_: any, i: number) => (
                            <Cell key={i} fill={i === 0 ? '#38bdf8' : '#0284c7'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">Component Loadings (Weights)</h3>
                  <div className="overflow-x-auto max-h-64 rounded-xl border border-slate-800">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="p-2.5">Feature</th>
                          {result.pca_report.loadings?.map((_: any, i: number) => (
                            <th key={i} className="p-2.5">PC {i + 1}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 font-mono text-slate-300">
                        {result.pca_report.input_features?.map((feat: string) => (
                          <tr key={feat} className="hover:bg-slate-800/30">
                            <td className="p-2.5 font-sans font-semibold text-slate-200">{feat}</td>
                            {result.pca_report.loadings?.map((l: any, i: number) => (
                              <td key={i} className="p-2.5">{l.loadings[feat] ?? '0.00'}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 3. Target Correlations */}
          {activeTab === 'correlations' && correlationChartData.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-slate-200">Top Feature Correlations with Target</h3>
              <div className="h-72 w-full bg-slate-950 p-4 rounded-xl border border-slate-800">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={correlationChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis type="number" domain={[-1, 1]} stroke="#64748b" fontSize={11} />
                    <YAxis dataKey="feature" type="category" stroke="#64748b" fontSize={11} width={140} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                      formatter={(v: any) => [`${v}`, 'Correlation']}
                    />
                    <Bar dataKey="correlation" fill="#10b981" radius={[0, 4, 4, 0]}>
                      {correlationChartData.map((entry: any, i: number) => (
                        <Cell key={i} fill={entry.correlation >= 0 ? '#10b981' : '#f43f5e'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 4. Pipeline Steps */}
          {activeTab === 'steps' && (
            <div className="space-y-3">
              {result?.steps?.map((step: any, idx: number) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 mt-0.5">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-slate-200">{step.message}</p>
                    {step.features?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {step.features.map((f: string) => (
                          <span key={f} className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-purple-300 font-mono">
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 5. Auto Candidate Features */}
          {activeTab === 'candidates' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" /> AI Candidate Feature Recommendations
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Heuristically generated high-signal interactions, non-linear powers, and temporal signals.
                  </p>
                </div>
                <div className="text-xs text-amber-400/90 font-medium px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  {candidates.length} candidates generated
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {candidates.map((cand, idx) => {
                  const isSelected = !!selectedCandidates[cand.name];
                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedCandidates(prev => ({ ...prev, [cand.name]: !prev[cand.name] }))}
                      className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                        isSelected
                          ? 'bg-amber-950/20 border-amber-500/50 shadow-md shadow-amber-500/5'
                          : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-slate-100 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            {cand.name}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${
                              cand.impact_score === 'high'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : cand.impact_score === 'medium'
                                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                                : 'bg-slate-700/50 text-slate-300'
                            }`}>
                              {cand.impact_score} Impact
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              {cand.type}
                            </span>
                          </div>
                        </div>

                        <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800/80">
                          <p className="text-[11px] font-mono text-amber-300/90">
                            {cand.formula}
                          </p>
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed">
                          {cand.rationale}
                        </p>
                      </div>

                      <div className="pt-3 mt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                        <span className="text-slate-500">
                          {isSelected ? '✓ Selected for generation' : 'Click card to select'}
                        </span>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="w-4 h-4 rounded text-amber-500 bg-slate-950 border-slate-700 focus:ring-0"
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Action Footer */}
        <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Transformations ready for model training pipeline.
          </p>
          <button
            onClick={() => navigate(`/experiments?dataset_id=${selectedDatasetId}`)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-medium text-xs shadow-lg shadow-sky-500/20 transition-all"
          >
            <span>Train AutoML Models with Features</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
