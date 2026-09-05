import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { 
  Eraser, AlertCircle, CheckCircle2, RefreshCw, Sparkles, ArrowRight, Loader2, 
  Layers, Plus, Trash2, ToggleLeft, ToggleRight, Eye, GitCommit, Play, X, Sliders
} from 'lucide-react';

export const Cleaning: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [issues, setIssues] = useState<any>(null);
  const [cleanResult, setCleanResult] = useState<any>(null);
  const [target, setTarget] = useState('');
  const [targets, setTargets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [cleaning, setCleaning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pipeline states
  const [pipelineSteps, setPipelineSteps] = useState<any[]>([]);
  const [loadingPipeline, setLoadingPipeline] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [selectedDiff, setSelectedDiff] = useState<any | null>(null);
  const [showAddStep, setShowAddStep] = useState(false);
  const [newOp, setNewOp] = useState({ operation: 'impute_missing', column: '', strategy: 'median', iqr_factor: 1.5 });

  useEffect(() => {
    apiService.getDatasets().then(r => {
      setDatasets(r.items || []);
      if (r.items?.length > 0) setSelectedDataset(r.items[0].id);
    });
  }, []);

  const loadPipeline = async (datasetId: string) => {
    setLoadingPipeline(true);
    try {
      const steps = await apiService.getPipeline(datasetId);
      setPipelineSteps(steps || []);
    } catch (e) {
      console.error("Failed to load pipeline steps", e);
    } finally {
      setLoadingPipeline(false);
    }
  };

  useEffect(() => {
    if (selectedDataset) {
      loadPipeline(selectedDataset);
    }
  }, [selectedDataset]);

  const loadIssues = async () => {
    if (!selectedDataset) return;
    setLoading(true);
    setError(null);
    try {
      const [issueData, suggestions] = await Promise.all([
        apiService.getCleaningIssues(selectedDataset),
        apiService.suggestTarget(selectedDataset),
      ]);
      setIssues(issueData);
      setTargets(suggestions);
      if (suggestions.length > 0) setTarget(suggestions[0].column);
      await loadPipeline(selectedDataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load issues');
    }
    setLoading(false);
  };

  const handleToggleStep = async (stepId: string, currentStatus: boolean) => {
    try {
      await apiService.updatePipelineStep(selectedDataset, stepId, { is_active: !currentStatus });
      await loadPipeline(selectedDataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to toggle step');
    }
  };

  const handleDeleteStep = async (stepId: string) => {
    try {
      await apiService.deletePipelineStep(selectedDataset, stepId);
      await loadPipeline(selectedDataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete step');
    }
  };

  const handleReplayPipeline = async () => {
    setReplaying(true);
    setError(null);
    try {
      const result = await apiService.replayPipeline(selectedDataset);
      setCleanResult({
        rows_before: result.initial_shape[0],
        rows_after: result.final_shape[0],
        cols_before: result.initial_shape[1],
        cols_after: result.final_shape[1],
        steps: result.steps?.map((s: any) => ({ message: `Executed ${s.operation}: ${s.status}` })) || []
      });
      await loadPipeline(selectedDataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Pipeline replay failed');
    } finally {
      setReplaying(false);
    }
  };

  const handleViewDiff = async (stepId: string) => {
    try {
      const diff = await apiService.getPipelineDiff(selectedDataset, stepId);
      setSelectedDiff(diff);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to compute diff');
    }
  };

  const handleAddStepSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const params: any = {};
      if (newOp.column) params.column = newOp.column;
      if (newOp.operation === 'impute_missing') params.strategy = newOp.strategy;
      if (newOp.operation === 'clip_outliers') params.iqr_factor = newOp.iqr_factor;

      await apiService.addPipelineStep(selectedDataset, {
        operation: newOp.operation,
        params
      });
      setShowAddStep(false);
      setNewOp({ operation: 'impute_missing', column: '', strategy: 'median', iqr_factor: 1.5 });
      await loadPipeline(selectedDataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add step');
    }
  };

  const applyCleaning = async () => {
    if (!selectedDataset || !target) return;
    setCleaning(true);
    setError(null);
    try {
      const result = await apiService.cleanDataset(selectedDataset, {
        target, drop_ids: true, drop_constants: true, remove_duplicates: true, handle_missing: 'auto',
      });
      setCleanResult(result);
      // Auto-register steps in pipeline if empty
      if (pipelineSteps.length === 0) {
        await apiService.addPipelineStep(selectedDataset, { operation: 'drop_duplicates' });
        if (issues?.potential_ids?.length > 0) {
          for (const pid of issues.potential_ids) {
            await apiService.addPipelineStep(selectedDataset, { operation: 'drop_column', params: { column: pid } });
          }
        }
        await apiService.addPipelineStep(selectedDataset, { operation: 'impute_missing', params: { strategy: 'median' } });
        await loadPipeline(selectedDataset);
      }
      try {
        const updatedIssues = await apiService.getCleaningIssues(selectedDataset);
        setIssues(updatedIssues);
      } catch { /* ignore */ }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Cleaning failed');
    }
    setCleaning(false);
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-2 mb-1">
          <Eraser className="w-5 h-5 text-emerald-400" />
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Data Quality</span>
        </div>
        <h1 className="text-3xl font-black text-slate-100 tracking-tight">Data Cleaning</h1>
        <p className="text-sm text-slate-400 mt-1">Detect and resolve data quality issues</p>
      </div>

      <div className="animate-fade-in-up stagger-1 flex items-center gap-4">
        <select value={selectedDataset} onChange={e => setSelectedDataset(e.target.value)}
          className="bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-4 py-2.5 text-sm focus:border-emerald-500/50 transition-colors">
          <option value="">Select dataset...</option>
          {datasets.map(d => <option key={d.id} value={d.id}>{d.original_filename}</option>)}
        </select>
        <button onClick={loadIssues} disabled={!selectedDataset || loading}
          className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition-all">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {loading ? 'Analyzing...' : 'Detect Issues'}
        </button>
      </div>

      {error && (
        <div className="animate-fade-in p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {issues && (
        <div className="space-y-6">
          {/* Issue Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Missing Values', value: `${issues.missing_percentage}%`, sub: `${issues.total_missing.toLocaleString()} cells`, color: 'amber' },
              { label: 'Duplicates', value: issues.duplicates.toLocaleString(), sub: `${issues.duplicate_percentage}% of rows`, color: 'rose' },
              { label: 'Potential IDs', value: issues.potential_ids.length, sub: 'columns detected', color: 'sky' },
              { label: 'Constant Columns', value: issues.constant_columns.length, sub: 'zero variance', color: 'slate' },
            ].map((card, idx) => (
              <div key={card.label} className={`animate-fade-in-up stagger-${idx + 1} glass-card border border-slate-800/50 rounded-xl p-4`}>
                <p className="text-xs text-slate-400 uppercase font-semibold">{card.label}</p>
                <p className={`text-2xl font-bold mt-1 text-${card.color}-400`}>{card.value}</p>
                <p className="text-xs text-slate-500 mt-1">{card.sub}</p>
              </div>
            ))}
          </div>

          {/* Missing Values Detail */}
          {issues.missing_details?.length > 0 && (
            <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-4">Missing Values by Column</h3>
              <div className="space-y-2.5">
                {issues.missing_details.map((d: any) => (
                  <div key={d.column} className="flex items-center justify-between">
                    <span className="text-sm text-slate-300 font-medium">{d.column}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-32 h-2.5 bg-slate-800/60 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-700" style={{ width: `${Math.min(d.percentage, 100)}%` }} />
                      </div>
                      <span className="text-xs text-slate-500 font-mono w-24 text-right">{d.count} ({d.percentage}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Target Selection & Clean */}
          <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-xl p-5">
            <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" /> Apply Recommended Cleaning
            </h3>
            <div className="flex items-center gap-4 mb-4">
              <label className="text-sm text-slate-400">Target column:</label>
              <select value={target} onChange={e => setTarget(e.target.value)}
                className="bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-3 py-2 text-sm">
                {targets.map(t => (
                  <option key={t.column} value={t.column}>{t.column} (confidence: {t.confidence})</option>
                ))}
              </select>
            </div>
            <div className="text-sm text-slate-400 space-y-1.5 mb-5 p-4 rounded-xl bg-slate-900/40 border border-slate-800/30">
              <p>• Remove <strong className="text-slate-300">{issues.duplicates}</strong> duplicate rows</p>
              <p>• Drop <strong className="text-slate-300">{issues.constant_columns.length}</strong> constant column(s)</p>
              <p>• Drop <strong className="text-slate-300">{issues.potential_ids.length}</strong> ID column(s)</p>
              <p>• Impute missing values (median for numerical, mode for categorical)</p>
            </div>
            <button onClick={applyCleaning} disabled={cleaning || !target}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition-all">
              {cleaning ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {cleaning ? 'Cleaning...' : 'Apply Recommended Cleaning'}
            </button>
          </div>

          {/* Reversible Cleaning Pipeline Studio */}
          <div className="animate-fade-in-up glass-card border border-emerald-500/20 rounded-2xl p-6 relative overflow-hidden bg-gradient-to-b from-slate-900/90 to-slate-950/90">
            <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                  <Layers className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    Reversible Cleaning Pipeline
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                      {pipelineSteps.length} Steps
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">Non-destructive, step-by-step DAG of data transformations with rollback</p>
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => setShowAddStep(!showAddStep)}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 transition-all shadow-sm"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Step
                </button>
                <button
                  onClick={handleReplayPipeline}
                  disabled={replaying || pipelineSteps.length === 0}
                  className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 transition-all"
                >
                  {replaying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  {replaying ? 'Replaying Pipeline...' : 'Replay All Active'}
                </button>
              </div>
            </div>

            {/* Add Step Form */}
            {showAddStep && (
              <form onSubmit={handleAddStepSubmit} className="mb-6 p-4 rounded-xl bg-slate-950/80 border border-slate-700/60 animate-fade-in space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5 text-emerald-400" /> New Pipeline Operation
                  </span>
                  <button type="button" onClick={() => setShowAddStep(false)} className="text-slate-400 hover:text-slate-200">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Operation</label>
                    <select
                      value={newOp.operation}
                      onChange={e => setNewOp({ ...newOp, operation: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
                    >
                      <option value="impute_missing">Impute Missing Values</option>
                      <option value="drop_duplicates">Drop Duplicate Rows</option>
                      <option value="drop_column">Drop Column</option>
                      <option value="clip_outliers">Clip Outliers (IQR)</option>
                      <option value="scale_standard">Standard Scale (Z-Score)</option>
                      <option value="one_hot_encode">One-Hot Encode</option>
                    </select>
                  </div>

                  {newOp.operation !== 'drop_duplicates' && (
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Target Column (or leave empty for all)</label>
                      <input
                        type="text"
                        placeholder="e.g. age, salary, id"
                        value={newOp.column}
                        onChange={e => setNewOp({ ...newOp, column: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
                      />
                    </div>
                  )}

                  {newOp.operation === 'impute_missing' && (
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Strategy</label>
                      <select
                        value={newOp.strategy}
                        onChange={e => setNewOp({ ...newOp, strategy: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
                      >
                        <option value="median">Median (Numerical)</option>
                        <option value="mean">Mean (Numerical)</option>
                        <option value="mode">Mode (Most Frequent)</option>
                        <option value="drop_rows">Drop Incomplete Rows</option>
                      </select>
                    </div>
                  )}

                  {newOp.operation === 'clip_outliers' && (
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">IQR Multiplier Factor</label>
                      <input
                        type="number"
                        step="0.1"
                        value={newOp.iqr_factor}
                        onChange={e => setNewOp({ ...newOp, iqr_factor: parseFloat(e.target.value) || 1.5 })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
                      />
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddStep(false)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300 hover:bg-slate-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white"
                  >
                    Append Step & Replay
                  </button>
                </div>
              </form>
            )}

            {/* Steps List */}
            {loadingPipeline ? (
              <div className="py-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-emerald-400" /> Loading pipeline steps...
              </div>
            ) : pipelineSteps.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400 border border-dashed border-slate-800 rounded-xl">
                No active pipeline steps registered yet. Click "Add Step" or run "Apply Recommended Cleaning" above to generate your pipeline.
              </div>
            ) : (
              <div className="space-y-2.5">
                {pipelineSteps.map((step: any, index: number) => (
                  <div
                    key={step.id}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all ${
                      step.is_active
                        ? 'bg-slate-900/60 border-slate-700/60 text-slate-200'
                        : 'bg-slate-950/40 border-slate-800/40 text-slate-500 opacity-60'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono font-bold flex items-center justify-center">
                        {index + 1}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold capitalize">
                            {step.operation.replace(/_/g, ' ')}
                          </span>
                          {step.is_active ? (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              Active
                            </span>
                          ) : (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                              Disabled
                            </span>
                          )}
                        </div>
                        {step.params && Object.keys(step.params).length > 0 && (
                          <p className="text-xs text-slate-400 font-mono mt-0.5">
                            {JSON.stringify(step.params)}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleViewDiff(step.id)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs text-sky-400 flex items-center gap-1 border border-slate-700/50 transition-colors"
                        title="View before/after diff"
                      >
                        <Eye className="w-3.5 h-3.5" /> Diff
                      </button>

                      <button
                        onClick={() => handleToggleStep(step.id, step.is_active)}
                        className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 transition-colors"
                        title={step.is_active ? "Deactivate step" : "Activate step"}
                      >
                        {step.is_active ? (
                          <ToggleRight className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <ToggleLeft className="w-5 h-5 text-slate-500" />
                        )}
                      </button>

                      <button
                        onClick={() => handleDeleteStep(step.id)}
                        className="p-1.5 rounded-lg hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
                        title="Remove step"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Diff Modal */}
          {selectedDiff && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
              <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <GitCommit className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-sm font-bold text-slate-100">
                      Step Transformation Diff: {selectedDiff.operation}
                    </h3>
                  </div>
                  <button onClick={() => setSelectedDiff(null)} className="text-slate-400 hover:text-slate-200">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <span className="text-slate-400 font-semibold block mb-1">Before Step</span>
                    <p className="text-slate-200">Rows: <strong className="font-mono">{selectedDiff.before?.shape[0]}</strong></p>
                    <p className="text-slate-200">Cols: <strong className="font-mono">{selectedDiff.before?.shape[1]}</strong></p>
                    <p className="text-slate-200">Missing cells: <strong className="font-mono">{selectedDiff.before?.total_missing}</strong></p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                    <span className="text-emerald-400 font-semibold block mb-1">After Step</span>
                    <p className="text-slate-200">Rows: <strong className="font-mono">{selectedDiff.after?.shape[0]}</strong></p>
                    <p className="text-slate-200">Cols: <strong className="font-mono">{selectedDiff.after?.shape[1]}</strong></p>
                    <p className="text-slate-200">Missing cells: <strong className="font-mono">{selectedDiff.after?.total_missing}</strong></p>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-slate-300 space-y-1">
                  <p className="font-semibold text-emerald-400">Impact Analysis:</p>
                  <p>• Rows change: <span className="font-mono font-bold text-slate-100">{selectedDiff.diff?.rows_delta}</span></p>
                  <p>• Columns change: <span className="font-mono font-bold text-slate-100">{selectedDiff.diff?.cols_delta}</span></p>
                  <p>• Missing values resolved: <span className="font-mono font-bold text-slate-100">{Math.abs(selectedDiff.diff?.missing_delta)}</span></p>
                  {selectedDiff.diff?.dropped_columns?.length > 0 && (
                    <p>• Dropped columns: <span className="font-mono text-rose-300">{selectedDiff.diff.dropped_columns.join(', ')}</span></p>
                  )}
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setSelectedDiff(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200"
                  >
                    Close Diff
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Cleaning Result */}
          {cleanResult && (
            <div className="animate-scale-in glass-card border border-emerald-500/30 rounded-xl p-5 bg-gradient-to-br from-emerald-500/5 to-transparent">
              <h3 className="text-sm font-bold text-emerald-400 mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5" /> Cleaning Complete! 🎉
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="text-center p-3 rounded-xl bg-slate-900/40">
                  <p className="text-xs text-slate-400">Rows Before</p>
                  <p className="text-lg font-bold text-slate-300">{cleanResult.rows_before?.toLocaleString()}</p>
                </div>
                <div className="text-center p-3 rounded-xl bg-slate-900/40">
                  <p className="text-xs text-slate-400">Rows After</p>
                  <p className="text-lg font-bold text-emerald-400">{cleanResult.rows_after?.toLocaleString()}</p>
                </div>
                <div className="text-center p-3 rounded-xl bg-slate-900/40">
                  <p className="text-xs text-slate-400">Cols Before</p>
                  <p className="text-lg font-bold text-slate-300">{cleanResult.cols_before}</p>
                </div>
                <div className="text-center p-3 rounded-xl bg-slate-900/40">
                  <p className="text-xs text-slate-400">Cols After</p>
                  <p className="text-lg font-bold text-emerald-400">{cleanResult.cols_after}</p>
                </div>
              </div>
              {cleanResult.steps?.map((step: any, i: number) => (
                <p key={i} className="text-sm text-slate-400 flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> {step.message}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {!issues && !loading && (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
            <Eraser className="w-8 h-8 text-emerald-400/60" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Issues Detected Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">Select a dataset and click "Detect Issues" to analyze data quality</p>
          <div className="flex items-center justify-center gap-2 text-emerald-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Select a dataset above to begin</span>
          </div>
        </div>
      )}
    </div>
  );
};
