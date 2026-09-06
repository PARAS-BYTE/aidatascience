import React, { useState, useEffect } from 'react';
import {
  Network, AlertTriangle, CheckCircle2, Zap,
  Loader2, BarChart2, ShieldAlert, Sliders, Database,
  Sparkles, Layers, ArrowRight, PlusCircle
} from 'lucide-react';
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, BarChart, Bar, CartesianGrid
} from 'recharts';
import { apiService } from '../services/api';
import { useDatasets } from '../hooks/useDatasets';

const CLUSTER_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6',
  '#EC4899', '#06B6D4', '#F97316', '#6366F1',
  '#14B8A6', '#84CC16',
];

export const Unsupervised: React.FC = () => {
  const { datasets, loading: loadingDatasets, refresh: refreshDatasets } = useDatasets();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'clustering' | 'anomalies' | 'pca'>('clustering');

  // Clustering state
  const [clusterAlgo, setClusterAlgo] = useState<'kmeans' | 'gmm' | 'agglomerative' | 'dbscan'>('kmeans');
  const [autoK, setAutoK] = useState<boolean>(true);
  const [manualK, setManualK] = useState<number>(3);
  const [clusteringResult, setClusteringResult] = useState<any>(null);
  const [loadingClustering, setLoadingClustering] = useState<boolean>(false);
  const [clusterColName, setClusterColName] = useState<string>('cluster_segment');
  const [augmentingClusters, setAugmentingClusters] = useState<boolean>(false);
  const [clusterAugmentSuccess, setClusterAugmentSuccess] = useState<string | null>(null);

  // Anomaly state
  const [anomalyAlgo, setAnomalyAlgo] = useState<'isolation_forest' | 'lof'>('isolation_forest');
  const [contamination, setContamination] = useState<number>(0.05);
  const [anomalyResult, setAnomalyResult] = useState<any>(null);
  const [loadingAnomalies, setLoadingAnomalies] = useState<boolean>(false);
  const [anomalyColName, setAnomalyColName] = useState<string>('is_anomaly');
  const [augmentingAnomalies, setAugmentingAnomalies] = useState<boolean>(false);
  const [anomalyAugmentSuccess, setAnomalyAugmentSuccess] = useState<string | null>(null);

  // PCA state
  const [pcaComponents, setPcaComponents] = useState<number>(2);
  const [pcaResult, setPcaResult] = useState<any>(null);
  const [loadingPca, setLoadingPca] = useState<boolean>(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Auto-select first dataset
  useEffect(() => {
    if (datasets.length > 0 && !selectedDatasetId) {
      setSelectedDatasetId(datasets[0].id);
    }
  }, [datasets, selectedDatasetId]);

  // Execute Clustering
  const handleRunClustering = async () => {
    if (!selectedDatasetId) return;
    try {
      setLoadingClustering(true);
      setErrorMsg(null);
      setClusterAugmentSuccess(null);
      const res = await apiService.runClustering(selectedDatasetId, {
        algorithm: clusterAlgo,
        auto_k: autoK,
        n_clusters: autoK ? undefined : manualK,
        k_min: 2,
        k_max: 8,
      });
      setClusteringResult(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to run clustering');
    } finally {
      setLoadingClustering(false);
    }
  };

  // Execute Anomaly Detection
  const handleRunAnomalies = async () => {
    if (!selectedDatasetId) return;
    try {
      setLoadingAnomalies(true);
      setErrorMsg(null);
      setAnomalyAugmentSuccess(null);
      const res = await apiService.runAnomalyDetection(selectedDatasetId, {
        algorithm: anomalyAlgo,
        contamination: contamination,
      });
      setAnomalyResult(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to detect anomalies');
    } finally {
      setLoadingAnomalies(false);
    }
  };

  // Execute PCA
  const handleRunPca = async () => {
    if (!selectedDatasetId) return;
    try {
      setLoadingPca(true);
      setErrorMsg(null);
      const res = await apiService.runPca(selectedDatasetId, {
        n_components: pcaComponents,
      });
      setPcaResult(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to compute PCA');
    } finally {
      setLoadingPca(false);
    }
  };

  // Augment Dataset with Cluster Labels
  const handleAugmentClusters = async () => {
    if (!selectedDatasetId || !clusteringResult?.cluster_labels) return;
    try {
      setAugmentingClusters(true);
      setErrorMsg(null);
      const res = await apiService.appendUnsupervisedColumn(selectedDatasetId, {
        column_name: clusterColName || 'cluster_label',
        values: clusteringResult.cluster_labels,
        change_summary: `Appended ${clusteringResult.algorithm.toUpperCase()} cluster segments (${clusteringResult.optimal_k} clusters)`,
      });
      setClusterAugmentSuccess(res.message);
      refreshDatasets();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to augment dataset with clusters');
    } finally {
      setAugmentingClusters(false);
    }
  };

  // Augment Dataset with Anomaly Flags
  const handleAugmentAnomalies = async () => {
    if (!selectedDatasetId || !anomalyResult?.anomaly_flags) return;
    try {
      setAugmentingAnomalies(true);
      setErrorMsg(null);
      const res = await apiService.appendUnsupervisedColumn(selectedDatasetId, {
        column_name: anomalyColName || 'is_anomaly',
        values: anomalyResult.anomaly_flags,
        change_summary: `Appended ${anomalyResult.algorithm.toUpperCase()} anomaly flags (${anomalyResult.anomaly_count} outliers)`,
      });
      setAnomalyAugmentSuccess(res.message);
      refreshDatasets();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to augment dataset with anomaly flag');
    } finally {
      setAugmentingAnomalies(false);
    }
  };

  const selectedDataset = datasets.find(d => d.id === selectedDatasetId);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-blue-600 font-semibold text-sm mb-1">
            <Network className="w-4 h-4" />
            <span>Label-Free Machine Learning</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Unsupervised Learning Studio
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            AutoML Clustering, Unsupervised Anomaly Detection, 2D/3D PCA &amp; Dataset Augmentation.
          </p>
        </div>

        {/* Dataset Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200">
            <Database className="w-4 h-4 text-slate-500" />
            <select
              value={selectedDatasetId}
              onChange={(e) => {
                setSelectedDatasetId(e.target.value);
                setClusteringResult(null);
                setAnomalyResult(null);
                setPcaResult(null);
                setClusterAugmentSuccess(null);
                setAnomalyAugmentSuccess(null);
              }}
              className="bg-transparent text-sm font-medium text-slate-800 outline-none cursor-pointer"
              disabled={loadingDatasets}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_filename} (v{d.version || 1})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700 text-sm">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('clustering')}
          className={`pb-3 text-sm font-medium transition-all flex items-center gap-2 border-b-2 ${
            activeTab === 'clustering'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Clustering &amp; Segmentation
        </button>
        <button
          onClick={() => setActiveTab('anomalies')}
          className={`pb-3 text-sm font-medium transition-all flex items-center gap-2 border-b-2 ${
            activeTab === 'anomalies'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          Anomaly &amp; Outlier Detection
        </button>
        <button
          onClick={() => setActiveTab('pca')}
          className={`pb-3 text-sm font-medium transition-all flex items-center gap-2 border-b-2 ${
            activeTab === 'pca'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Layers className="w-4 h-4" />
          Dimensionality Reduction (PCA)
        </button>
      </div>

      {/* ─── TAB 1: CLUSTERING ────────────────────────────────────────── */}
      {activeTab === 'clustering' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                  Algorithm
                </label>
                <select
                  value={clusterAlgo}
                  onChange={(e: any) => setClusterAlgo(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-800"
                >
                  <option value="kmeans">K-Means (Fast &amp; Scalable)</option>
                  <option value="gmm">Gaussian Mixture Models (GMM)</option>
                  <option value="agglomerative">Agglomerative Hierarchical</option>
                  <option value="dbscan">DBSCAN (Density-Based)</option>
                </select>
              </div>

              {clusterAlgo !== 'dbscan' && (
                <div className="flex items-center gap-3 pt-4">
                  <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={autoK}
                      onChange={(e) => setAutoK(e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
                    />
                    <span>Auto-K Optimizer (Sweep k=2..8)</span>
                  </label>

                  {!autoK && (
                    <div className="flex items-center gap-2 pl-2">
                      <span className="text-xs text-slate-500 font-medium">Clusters:</span>
                      <input
                        type="number"
                        min={2}
                        max={10}
                        value={manualK}
                        onChange={(e) => setManualK(parseInt(e.target.value) || 3)}
                        className="w-16 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-sm font-medium text-center"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            <button
              onClick={handleRunClustering}
              disabled={loadingClustering || !selectedDatasetId}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-5 py-2.5 rounded-xl shadow-sm hover:shadow transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {loadingClustering ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Discovering Clusters...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run Clustering AutoML</span>
                </>
              )}
            </button>
          </div>

          {/* Clustering Results */}
          {clusteringResult && (
            <div className="space-y-6">
              {/* Metric KPIs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Optimal Clusters
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1 flex items-baseline gap-2">
                    {clusteringResult.optimal_k}
                    <span className="text-xs font-normal text-slate-500">
                      ({clusteringResult.algorithm.toUpperCase()})
                    </span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Silhouette Score
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1 flex items-baseline gap-2">
                    {clusteringResult.metrics.silhouette_score}
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                        clusteringResult.metrics.cluster_separation_rating === 'Strong'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : clusteringResult.metrics.cluster_separation_rating === 'Moderate'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {clusteringResult.metrics.cluster_separation_rating}
                    </span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Davies-Bouldin Index
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1">
                    {clusteringResult.metrics.davies_bouldin_index}
                    <span className="text-xs font-normal text-slate-400 ml-2">
                      (Lower = crisper)
                    </span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Calinski-Harabasz
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1">
                    {clusteringResult.metrics.calinski_harabasz}
                    <span className="text-xs font-normal text-slate-400 ml-2">
                      (Variance ratio)
                    </span>
                  </div>
                </div>
              </div>

              {/* 2D Cluster Visualization + Auto-K Chart */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* 2D Projection Scatter */}
                <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">
                        2D PCA Cluster Projection
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Dimensionality reduced to 2 principal components (Total Variance Explained:{' '}
                        {clusteringResult.pca_projection.total_variance_explained}%)
                      </p>
                    </div>
                  </div>

                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis
                          type="number"
                          dataKey="x"
                          name="PC1"
                          stroke="#94a3b8"
                          fontSize={12}
                          tickLine={false}
                        />
                        <YAxis
                          type="number"
                          dataKey="y"
                          name="PC2"
                          stroke="#94a3b8"
                          fontSize={12}
                          tickLine={false}
                        />
                        <Tooltip
                          cursor={{ strokeDasharray: '3 3' }}
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-slate-900/90 backdrop-blur-md text-white px-3 py-2 rounded-lg text-xs shadow-lg">
                                  <div className="font-semibold text-blue-300">
                                    Row #{data.row_index}
                                  </div>
                                  <div>Cluster: {data.cluster === -1 ? 'Noise (-1)' : `Cluster ${data.cluster}`}</div>
                                  <div className="text-slate-400">
                                    PC1: {data.x}, PC2: {data.y}
                                  </div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Scatter
                          name="Clusters"
                          data={clusteringResult.pca_projection.points}
                          fill="#8884d8"
                        >
                          {clusteringResult.pca_projection.points.map((entry: any, index: number) => {
                            const color =
                              entry.cluster === -1
                                ? '#94A3B8'
                                : CLUSTER_COLORS[entry.cluster % CLUSTER_COLORS.length];
                            return <Cell key={`cell-${index}`} fill={color} />;
                          })}
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Cluster Legend */}
                  <div className="flex flex-wrap items-center justify-center gap-4 mt-4 pt-3 border-t border-slate-100">
                    {Object.entries(clusteringResult.cluster_distribution).map(
                      ([cId, count]: any) => {
                        const numId = parseInt(cId);
                        const color =
                          numId === -1
                            ? '#94A3B8'
                            : CLUSTER_COLORS[numId % CLUSTER_COLORS.length];
                        return (
                          <div key={cId} className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                            <span
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: color }}
                            />
                            <span>
                              {numId === -1 ? 'Noise' : `Cluster ${numId}`}: {count} rows
                            </span>
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>

                {/* Auto-K Optimization Curve */}
                <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">
                      Auto-K Optimization
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Silhouette score evaluation curve across candidate cluster counts ($k$).
                    </p>

                    <div className="h-60 w-full mt-4">
                      {clusteringResult.optimization_curve &&
                      clusteringResult.optimization_curve.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={clusteringResult.optimization_curve}
                            margin={{ top: 10, right: 10, bottom: 20, left: 0 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                            <XAxis
                              dataKey="k"
                              stroke="#94a3b8"
                              fontSize={11}
                              label={{ value: 'Number of Clusters (k)', position: 'insideBottom', offset: -10, fontSize: 11 }}
                            />
                            <YAxis
                              stroke="#94a3b8"
                              fontSize={11}
                              domain={[0, 1]}
                            />
                            <Tooltip
                              formatter={(val: any) => [val, 'Silhouette Score']}
                              labelFormatter={(label) => `k = ${label} clusters`}
                            />
                            <Bar dataKey="silhouette_score" fill="#3B82F6" radius={[4, 4, 0, 0]}>
                              {clusteringResult.optimization_curve.map((entry: any, index: number) => (
                                <Cell
                                  key={`k-cell-${index}`}
                                  fill={
                                    entry.k === clusteringResult.optimal_k
                                      ? '#10B981'
                                      : '#3B82F6'
                                  }
                                />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-xs text-slate-400">
                          Auto-K curve available when Auto-K is enabled.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 p-3 bg-emerald-50 rounded-xl border border-emerald-100 flex items-center gap-2 text-xs text-emerald-800">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>
                      Highest silhouette score observed at <strong>k = {clusteringResult.optimal_k}</strong>.
                    </span>
                  </div>
                </div>
              </div>

              {/* Cluster Personas & Insights */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-5 h-5 text-amber-500" />
                  <h3 className="text-base font-semibold text-slate-900">
                    Automated Segment Personas
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {clusteringResult.cluster_personas?.map((p: any) => {
                    const color = CLUSTER_COLORS[p.cluster_id % CLUSTER_COLORS.length];
                    return (
                      <div
                        key={p.cluster_id}
                        className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span
                              className="px-2.5 py-0.5 rounded-full text-xs font-bold text-white shadow-xs"
                              style={{ backgroundColor: color }}
                            >
                              Cluster #{p.cluster_id}
                            </span>
                            <span className="text-xs font-semibold text-slate-600">
                              {p.count} records ({p.percentage}%)
                            </span>
                          </div>

                          <h4 className="font-semibold text-slate-900 text-sm mt-2">
                            {p.title}
                          </h4>
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                            {p.summary}
                          </p>
                        </div>

                        {p.distinctive_traits && p.distinctive_traits.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-slate-200/80 space-y-1.5">
                            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                              Key Distinctive Features
                            </div>
                            {p.distinctive_traits.map((trait: any, tIdx: number) => (
                              <div
                                key={tIdx}
                                className="flex items-center justify-between text-xs bg-white p-1.5 rounded-lg border border-slate-200/60"
                              >
                                <span className="font-medium text-slate-700 truncate mr-2">
                                  {trait.feature}
                                </span>
                                <span
                                  className={`font-semibold shrink-0 ${
                                    trait.diff_pct > 0 ? 'text-emerald-600' : 'text-rose-600'
                                  }`}
                                >
                                  {trait.diff_pct > 0 ? `+${trait.diff_pct}%` : `${trait.diff_pct}%`}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Augmentation Action Card */}
              <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 p-6 rounded-2xl border border-blue-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-blue-700 font-semibold text-sm">
                    <PlusCircle className="w-4 h-4" />
                    <span>Dataset Augmentation Pipeline</span>
                  </div>
                  <h4 className="text-base font-bold text-slate-900">
                    Save Cluster Assignments as a New Feature
                  </h4>
                  <p className="text-xs text-slate-600 max-w-xl">
                    Append this cluster membership column to your dataset and create an automated
                    new version snapshot (v{(selectedDataset?.version || 1) + 1}) for downstream AutoML models.
                  </p>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                  <input
                    type="text"
                    value={clusterColName}
                    onChange={(e) => setClusterColName(e.target.value)}
                    placeholder="Column name (e.g. cluster_id)"
                    className="px-3 py-2 text-sm bg-white border border-slate-300 rounded-xl font-mono text-slate-800 outline-none focus:border-blue-500 w-44"
                  />
                  <button
                    onClick={handleAugmentClusters}
                    disabled={augmentingClusters}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-xl text-sm shadow-sm flex items-center gap-2 whitespace-nowrap disabled:opacity-50"
                  >
                    {augmentingClusters ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Augmenting...</span>
                      </>
                    ) : (
                      <>
                        <ArrowRight className="w-4 h-4" />
                        <span>Save as Feature</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Augment Success Message */}
              {clusterAugmentSuccess && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <span>{clusterAugmentSuccess}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ─── TAB 2: ANOMALY DETECTION ─────────────────────────────────── */}
      {activeTab === 'anomalies' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-6">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                  Detection Algorithm
                </label>
                <select
                  value={anomalyAlgo}
                  onChange={(e: any) => setAnomalyAlgo(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-800"
                >
                  <option value="isolation_forest">Isolation Forest (Ensemble Tree Isolation)</option>
                  <option value="lof">Local Outlier Factor (LOF Density)</option>
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Contamination Rate
                  </label>
                  <span className="text-xs font-bold text-blue-600 font-mono ml-2">
                    {(contamination * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0.01}
                    max={0.25}
                    step={0.01}
                    value={contamination}
                    onChange={(e) => setContamination(parseFloat(e.target.value))}
                    className="w-36 accent-blue-600 cursor-pointer"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleRunAnomalies}
              disabled={loadingAnomalies || !selectedDatasetId}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-5 py-2.5 rounded-xl shadow-sm hover:shadow transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {loadingAnomalies ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Scanning Records...</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-4 h-4" />
                  <span>Scan for Outliers</span>
                </>
              )}
            </button>
          </div>

          {/* Anomaly Results */}
          {anomalyResult && (
            <div className="space-y-6">
              {/* KPIs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Total Records
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1">
                    {anomalyResult.total_rows}
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Anomalies Flagged
                  </div>
                  <div className="text-2xl font-bold text-rose-600 mt-1 flex items-baseline gap-2">
                    {anomalyResult.anomaly_count}
                    <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                      {anomalyResult.anomaly_percentage}%
                    </span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Contamination Baseline
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1">
                    {(anomalyResult.contamination_rate * 100).toFixed(0)}%
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Dataset Health
                  </div>
                  <div className="text-lg font-bold text-slate-900 mt-2 flex items-center gap-2">
                    {anomalyResult.anomaly_count > 0 ? (
                      <span className="text-amber-600 flex items-center gap-1 text-sm font-semibold">
                        <AlertTriangle className="w-4 h-4" /> Outliers Identified
                      </span>
                    ) : (
                      <span className="text-emerald-600 flex items-center gap-1 text-sm font-semibold">
                        <CheckCircle2 className="w-4 h-4" /> Clean Population
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* 2D Projection & Top Anomalies Table */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* 2D Scatter of Normal vs Anomalies */}
                <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">
                        2D Outlier Dispersion Space
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Normal observations (slate) vs. High-confidence outliers (crimson).
                      </p>
                    </div>
                  </div>

                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis
                          type="number"
                          dataKey="x"
                          name="PC1"
                          stroke="#94a3b8"
                          fontSize={12}
                          tickLine={false}
                        />
                        <YAxis
                          type="number"
                          dataKey="y"
                          name="PC2"
                          stroke="#94a3b8"
                          fontSize={12}
                          tickLine={false}
                        />
                        <Tooltip
                          cursor={{ strokeDasharray: '3 3' }}
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-slate-900/90 backdrop-blur-md text-white px-3 py-2 rounded-lg text-xs shadow-lg">
                                  <div className="font-semibold text-blue-300">
                                    Row #{data.row_index}
                                  </div>
                                  <div>
                                    Status:{' '}
                                    <span
                                      className={data.is_anomaly ? 'text-rose-400 font-bold' : 'text-emerald-400'}
                                    >
                                      {data.is_anomaly ? 'Outlier' : 'Normal'}
                                    </span>
                                  </div>
                                  <div className="text-slate-400">Score: {data.score}</div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Scatter
                          name="Outliers"
                          data={anomalyResult.pca_projection.points}
                          fill="#8884d8"
                        >
                          {anomalyResult.pca_projection.points.map((entry: any, index: number) => {
                            const color = entry.is_anomaly ? '#EF4444' : '#94A3B8';
                            return <Cell key={`anomaly-cell-${index}`} fill={color} />;
                          })}
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="flex items-center justify-center gap-6 mt-4 pt-3 border-t border-slate-100 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-slate-400" />
                      <span className="text-slate-600">Inliers (Normal Data)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-rose-500" />
                      <span className="font-semibold text-rose-600">
                        Outliers ({anomalyResult.anomaly_count})
                      </span>
                    </div>
                  </div>
                </div>

                {/* Top Anomalies Table */}
                <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">
                      Highest-Severity Outliers
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Top ranking records with extreme isolation scores.
                    </p>

                    <div className="mt-4 overflow-y-auto max-h-72 border border-slate-200 rounded-xl">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                          <tr>
                            <th className="px-3 py-2">Row #</th>
                            <th className="px-3 py-2">Score</th>
                            <th className="px-3 py-2">Feature Snippet</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {anomalyResult.top_anomalies && anomalyResult.top_anomalies.length > 0 ? (
                            anomalyResult.top_anomalies.map((item: any) => (
                              <tr key={item.row_index} className="hover:bg-rose-50/40">
                                <td className="px-3 py-2 font-mono font-bold text-rose-600">
                                  #{item.row_index}
                                </td>
                                <td className="px-3 py-2 font-mono text-slate-700">
                                  {item.anomaly_score}
                                </td>
                                <td className="px-3 py-2 text-slate-500 truncate max-w-[150px]">
                                  {Object.entries(item.data || {})
                                    .map(([k, v]) => `${k}: ${v}`)
                                    .slice(0, 2)
                                    .join(' | ')}
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={3} className="px-3 py-6 text-center text-slate-400">
                                No outliers detected at this contamination threshold.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Augment Anomaly Feature */}
                  <div className="mt-4 pt-4 border-t border-slate-100">
                    <div className="flex items-center gap-2 mb-2">
                      <Zap className="w-4 h-4 text-blue-600" />
                      <span className="text-xs font-semibold text-slate-800">
                        Add `is_anomaly` Flag to Dataset
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={anomalyColName}
                        onChange={(e) => setAnomalyColName(e.target.value)}
                        className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800 outline-none flex-1"
                      />
                      <button
                        onClick={handleAugmentAnomalies}
                        disabled={augmentingAnomalies}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-3 py-1.5 rounded-lg text-xs shadow-xs flex items-center gap-1 whitespace-nowrap disabled:opacity-50"
                      >
                        {augmentingAnomalies ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <ArrowRight className="w-3.5 h-3.5" />
                        )}
                        <span>Save Flag</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Anomaly Augment Success */}
              {anomalyAugmentSuccess && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <span>{anomalyAugmentSuccess}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ─── TAB 3: DIMENSIONALITY REDUCTION (PCA) ───────────────────── */}
      {activeTab === 'pca' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                  Components
                </label>
                <select
                  value={pcaComponents}
                  onChange={(e) => setPcaComponents(parseInt(e.target.value) || 2)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-800"
                >
                  <option value={2}>2 Components (2D Plane)</option>
                  <option value={3}>3 Components (3D Volume)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleRunPca}
              disabled={loadingPca || !selectedDatasetId}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-5 py-2.5 rounded-xl shadow-sm hover:shadow transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {loadingPca ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Computing Projections...</span>
                </>
              ) : (
                <>
                  <Sliders className="w-4 h-4" />
                  <span>Compute PCA Decomposition</span>
                </>
              )}
            </button>
          </div>

          {/* PCA Results */}
          {pcaResult && (
            <div className="space-y-6">
              {/* Variance KPIs */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Total Variance Preserved
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-1 flex items-baseline gap-2">
                    {pcaResult.total_variance_explained}%
                    <span className="text-xs text-emerald-600 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      {pcaResult.total_variance_explained >= 70 ? 'High Fidelity' : 'Moderate Fidelity'}
                    </span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    PC1 Variance
                  </div>
                  <div className="text-2xl font-bold text-blue-600 mt-1">
                    {pcaResult.explained_variance_pct[0]}%
                  </div>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    PC2 Variance
                  </div>
                  <div className="text-2xl font-bold text-indigo-600 mt-1">
                    {pcaResult.explained_variance_pct[1]}%
                  </div>
                </div>
              </div>

              {/* Scree Plot & Feature Loadings */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* 2D Projection */}
                <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">
                        PCA Latent Space Projection
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        First two principal axes capturing dominant orthogonal variance.
                      </p>
                    </div>
                  </div>

                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis
                          type="number"
                          dataKey="pc1"
                          name="PC1"
                          stroke="#94a3b8"
                          fontSize={12}
                          tickLine={false}
                        />
                        <YAxis
                          type="number"
                          dataKey="pc2"
                          name="PC2"
                          stroke="#94a3b8"
                          fontSize={12}
                          tickLine={false}
                        />
                        <Tooltip
                          cursor={{ strokeDasharray: '3 3' }}
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-slate-900/90 backdrop-blur-md text-white px-3 py-2 rounded-lg text-xs shadow-lg">
                                  <div className="font-semibold text-blue-300">
                                    Row #{data.row_index}
                                  </div>
                                  <div>PC1: {data.pc1}</div>
                                  <div>PC2: {data.pc2}</div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Scatter
                          name="PCA Coordinates"
                          data={pcaResult.points}
                          fill="#3B82F6"
                        />
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Feature Loadings Breakdown */}
                <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">
                      Dominant Feature Loadings
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Features exerting the strongest mathematical weight on Principal Component 1.
                    </p>

                    <div className="mt-4 space-y-3">
                      {pcaResult.feature_loadings?.PC1?.slice(0, 5).map((f: any, idx: number) => {
                        const absLoad = Math.min(100, Math.abs(f.loading) * 100);
                        return (
                          <div key={idx} className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-medium text-slate-700 truncate max-w-[200px]">
                                {f.feature}
                              </span>
                              <span
                                className={`font-mono font-semibold ${
                                  f.loading > 0 ? 'text-blue-600' : 'text-purple-600'
                                }`}
                              >
                                {f.loading > 0 ? `+${f.loading}` : f.loading} ({f.impact})
                              </span>
                            </div>
                            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  f.loading > 0 ? 'bg-blue-600' : 'bg-purple-600'
                                }`}
                                style={{ width: `${absLoad}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-200/60 text-xs text-slate-600">
                    <div className="font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                      <BarChart2 className="w-3.5 h-3.5 text-blue-600" />
                      Interpreting Loadings
                    </div>
                    Loadings close to ±1 indicate features with maximal influence on the directional spread
                    of the dataset.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Unsupervised;
