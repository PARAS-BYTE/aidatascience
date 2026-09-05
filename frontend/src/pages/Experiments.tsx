import React, { useEffect, useState, useCallback } from 'react';
import { apiService } from '../services/api';
import {
  FlaskConical, Play, Trophy, Clock, AlertCircle, Activity,
  Database, Cog, BarChart3, CheckCircle2, Loader2, Sparkles,
  Cpu, ArrowRight, Target, Award, Download, FileCode, Timer, Filter
} from 'lucide-react';

// ─── Training Pipeline Step Component ──────────────────
interface PipelineStep {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  status: 'pending' | 'running' | 'complete' | 'error';
}

const TrainingPipelineVisualizer: React.FC<{
  steps: PipelineStep[];
  progress: number;
  progressMessage: string;
}> = ({ steps, progress, progressMessage }) => {
  return (
    <div className="space-y-6 p-6 rounded-2xl glass-card border border-slate-800/50 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-purple-500 to-pink-500 text-white animate-train-pulse shadow-lg shadow-purple-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Training Pipeline Active</h3>
            <p className="text-xs text-slate-400 mt-0.5">{progressMessage || 'Initializing...'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-right">
            <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-purple-400">
              {Math.round(progress)}%
            </span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="w-full h-2 bg-slate-800/80 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out relative"
            style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #38bdf8, #a855f7, #ec4899)',
              backgroundSize: '200% 100%',
              animation: 'gradientShift 2s ease infinite',
            }}
          >
            {/* Shimmer effect */}
            <div
              className="absolute inset-0 opacity-30"
              style={{
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
                backgroundSize: '200% 100%',
                animation: 'shimmer 1.5s ease-in-out infinite',
              }}
            />
          </div>
        </div>

        {/* Floating particles during training */}
        <div className="absolute -top-6 left-0 right-0 h-8 overflow-hidden pointer-events-none">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="particle"
              style={{
                left: `${Math.random() * 100}%`,
                backgroundColor: ['#38bdf8', '#a855f7', '#34d399', '#f59e0b'][i % 4],
                animationDelay: `${Math.random() * 2}s`,
                animationDuration: `${1.5 + Math.random() * 1.5}s`,
              }}
            />
          ))}
        </div>
      </div>

      {/* Pipeline Steps */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {steps.map((step, idx) => (
          <div
            key={step.id}
            className={`relative p-4 rounded-xl border transition-all duration-500 ${
              step.status === 'running'
                ? 'glass-card border-sky-500/30 pipeline-active animate-border-glow'
                : step.status === 'complete'
                ? 'glass-card border-emerald-500/30 pipeline-complete'
                : step.status === 'error'
                ? 'glass-card border-rose-500/30'
                : 'bg-slate-900/30 border-slate-800/50'
            }`}
            style={{ animationDelay: `${idx * 0.1}s` }}
          >
            {/* Step number */}
            <div className={`absolute -top-2 -left-1 w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold ${
              step.status === 'complete' ? 'bg-emerald-500 text-white' :
              step.status === 'running' ? 'bg-sky-500 text-white animate-pulse' :
              step.status === 'error' ? 'bg-rose-500 text-white' :
              'bg-slate-700 text-slate-400'
            }`}>
              {step.status === 'complete' ? '✓' : idx + 1}
            </div>

            <div className="flex flex-col items-center text-center gap-2">
              {/* Icon */}
              <div className={`transition-all duration-300 ${
                step.status === 'running' ? 'animate-bounce-subtle text-sky-400' :
                step.status === 'complete' ? 'text-emerald-400' :
                step.status === 'error' ? 'text-rose-400' :
                'text-slate-600'
              }`}>
                {step.status === 'running' ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : step.status === 'complete' ? (
                  <CheckCircle2 className="w-6 h-6" />
                ) : (
                  step.icon
                )}
              </div>

              {/* Label */}
              <div>
                <p className={`text-[11px] font-semibold transition-colors ${
                  step.status === 'running' ? 'text-sky-300' :
                  step.status === 'complete' ? 'text-emerald-300' :
                  'text-slate-400'
                }`}>
                  {step.label}
                </p>
                <p className="text-[9px] text-slate-500 mt-0.5">{step.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Main Experiments Component ──────────────────────
export const Experiments: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [target, setTarget] = useState('');
  const [targets, setTargets] = useState<any[]>([]);
  const [metric, setMetric] = useState('');
  const [leaderboard, setLeaderboard] = useState<any>(null);
  const [experiments, setExperiments] = useState<any[]>([]);
  const [trainingJob, setTrainingJob] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCelebration, setShowCelebration] = useState(false);
  const [budgetSeconds, setBudgetSeconds] = useState<number | undefined>(undefined);
  const [funnelData, setFunnelData] = useState<any[]>([]);

  // Pipeline state
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([
    { id: 'load', label: 'Data Loading', description: 'Loading dataset', icon: <Database className="w-6 h-6" />, status: 'pending' },
    { id: 'preprocess', label: 'Preprocessing', description: 'Clean & encode', icon: <Cog className="w-6 h-6" />, status: 'pending' },
    { id: 'split', label: 'Train/Test Split', description: 'Cross-validation', icon: <Target className="w-6 h-6" />, status: 'pending' },
    { id: 'train', label: 'Model Training', description: 'Fitting algorithms', icon: <Cpu className="w-6 h-6" />, status: 'pending' },
    { id: 'eval', label: 'Evaluation', description: 'Scoring metrics', icon: <BarChart3 className="w-6 h-6" />, status: 'pending' },
  ]);

  useEffect(() => {
    apiService.getDatasets().then(r => {
      setDatasets(r.items || []);
      if (r.items?.length > 0) setSelectedDataset(r.items[0].id);
    });
    apiService.getExperiments().then(setExperiments).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedDataset) {
      apiService.suggestTarget(selectedDataset).then(s => {
        setTargets(s);
        if (s.length > 0) setTarget(s[0].column);
      }).catch(() => {});
      // Gracefully handle 404 for leaderboard
      apiService.getLeaderboard(selectedDataset)
        .then(setLeaderboard)
        .catch(() => setLeaderboard(null));
    }
  }, [selectedDataset]);

  // Update pipeline steps based on progress
  const updatePipelineFromProgress = useCallback((progress: number, _message: string) => {
    setPipelineSteps(prev => prev.map(step => {
      if (step.id === 'load') {
        if (progress >= 10) return { ...step, status: 'complete' };
        if (progress >= 1) return { ...step, status: 'running' };
      }
      if (step.id === 'preprocess') {
        if (progress >= 30) return { ...step, status: 'complete' };
        if (progress >= 10) return { ...step, status: 'running' };
      }
      if (step.id === 'split') {
        if (progress >= 40) return { ...step, status: 'complete' };
        if (progress >= 30) return { ...step, status: 'running' };
      }
      if (step.id === 'train') {
        if (progress >= 85) return { ...step, status: 'complete' };
        if (progress >= 40) return { ...step, status: 'running' };
      }
      if (step.id === 'eval') {
        if (progress >= 98) return { ...step, status: 'complete' };
        if (progress >= 85) return { ...step, status: 'running' };
      }
      return step;
    }));
  }, []);

  const startTraining = async () => {
    if (!selectedDataset || !target) return;
    setLoading(true);
    setError(null);
    setShowCelebration(false);
    // Reset pipeline steps
    setPipelineSteps(prev => prev.map(s => ({ ...s, status: 'pending' })));

    try {
      const job = await apiService.trainModels({
        dataset_id: selectedDataset, 
        target, 
        primary_metric: metric || undefined,
        budget_seconds: budgetSeconds,
      });
      setTrainingJob(job);
      pollJob(job.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Training failed');
      setLoading(false);
    }
  };

  const pollJob = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await apiService.getJob(jobId);
        setTrainingJob(job);
        updatePipelineFromProgress(job.progress || 0, job.progress_message || '');

        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          clearInterval(interval);
          setLoading(false);
          if (job.status === 'COMPLETED') {
            // Mark all steps complete
            setPipelineSteps(prev => prev.map(s => ({ ...s, status: 'complete' })));
            setShowCelebration(true);
            setTimeout(() => setShowCelebration(false), 5000);

            if (job.result_data) {
              try {
                const parsed = JSON.parse(job.result_data);
                if (parsed.survival_funnel && parsed.survival_funnel.length > 0) {
                  setFunnelData(parsed.survival_funnel);
                }
              } catch (e) {}
            }

            const lb = await apiService.getLeaderboard(selectedDataset).catch(() => null);
            if (lb) setLeaderboard(lb);
            const exps = await apiService.getExperiments(selectedDataset).catch(() => []);
            setExperiments(exps);
          }
          if (job.status === 'FAILED') {
            setPipelineSteps(prev => {
              const running = prev.findIndex(s => s.status === 'running');
              if (running >= 0) {
                const updated = [...prev];
                updated[running] = { ...updated[running], status: 'error' };
                return updated;
              }
              return prev;
            });
            setError(job.error_message || 'Training failed');
          }
        }
      } catch { clearInterval(interval); setLoading(false); }
    }, 2000);
  };

  const registerModel = async (experimentId: string) => {
    try {
      await apiService.registerModel(experimentId);
      alert('Model registered successfully!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Registration failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="w-5 h-5 text-purple-400" />
          <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">Machine Learning</span>
        </div>
        <h1 className="text-3xl font-black text-slate-100 tracking-tight">Experiments</h1>
        <p className="text-sm text-slate-400 mt-1">Train models with real cross-validation and evaluation</p>
      </div>

      {/* Training Config */}
      <div className="animate-fade-in-up stagger-1 glass-card border border-slate-800/50 rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-5">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h3 className="text-sm font-bold text-slate-200">Train New Models</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5 mb-5">
          <div>
            <label className="text-xs text-slate-400 block mb-1.5 font-medium">Dataset</label>
            <select value={selectedDataset} onChange={e => setSelectedDataset(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-3 py-2.5 text-sm focus:border-purple-500/50 transition-colors">
              {datasets.map(d => <option key={d.id} value={d.id}>{d.original_filename}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5 font-medium">Target Column</label>
            <select value={target} onChange={e => setTarget(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-3 py-2.5 text-sm focus:border-purple-500/50 transition-colors">
              {targets.map(t => <option key={t.column} value={t.column}>{t.column}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5 font-medium">Primary Metric</label>
            <select value={metric} onChange={e => setMetric(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-3 py-2.5 text-sm focus:border-purple-500/50 transition-colors">
              <option value="">Auto-detect</option>
              <option value="f1">F1 Score</option>
              <option value="accuracy">Accuracy</option>
              <option value="precision">Precision</option>
              <option value="recall">Recall</option>
              <option value="roc_auc">ROC-AUC</option>
              <option value="r2">R²</option>
              <option value="rmse">RMSE</option>
              <option value="mae">MAE</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5 font-medium flex items-center gap-1">
              <Timer className="w-3.5 h-3.5 text-purple-400" /> AutoML Budget
            </label>
            <select
              value={budgetSeconds === undefined ? "" : String(budgetSeconds)}
              onChange={e => setBudgetSeconds(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full bg-slate-900/80 border border-slate-700/60 text-slate-200 rounded-xl px-3 py-2.5 text-sm focus:border-purple-500/50 transition-colors"
            >
              <option value="">Unlimited (Standard)</option>
              <option value="60">60s (Fast Halving)</option>
              <option value="120">120s (Balanced Budget)</option>
              <option value="300">300s (Thorough Search)</option>
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={startTraining} disabled={loading || !target}
              className="w-full px-5 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-xl text-sm font-semibold disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20 transition-all card-hover">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {loading ? 'Training...' : 'Train Models'}
            </button>
          </div>
        </div>
      </div>

      {/* Animated Training Pipeline */}
      {trainingJob && loading && (
        <TrainingPipelineVisualizer
          steps={pipelineSteps}
          progress={trainingJob.progress || 0}
          progressMessage={trainingJob.progress_message || 'Processing...'}
        />
      )}

      {/* Celebration banner */}
      {showCelebration && (
        <div className="animate-scale-in p-5 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-sky-500/10 to-purple-500/10 border border-emerald-500/30 flex items-center gap-4">
          <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400 animate-bounce-subtle">
            <Award className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-base font-bold text-emerald-300">Training Complete! 🎉</h3>
            <p className="text-sm text-slate-400 mt-0.5">All models have been trained and evaluated. Check the leaderboard below.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="animate-fade-in p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div>
            <p className="font-semibold">Training Error</p>
            <p className="text-rose-400/80 text-xs mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Leaderboard */}
      {leaderboard?.entries?.length > 0 && (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-400" /> Model Leaderboard
            </h3>
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="px-2 py-1 rounded-lg bg-slate-800/60 border border-slate-700/50">
                Task: <strong className="text-slate-300">{leaderboard.task_type}</strong>
              </span>
              <span className="px-2 py-1 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
                Metric: <strong>{leaderboard.primary_metric}</strong>
              </span>
            </div>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-800/50">
            <table className="w-full text-sm text-left text-slate-300">
              <thead className="text-xs text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800/50">
                <tr>
                  <th className="px-4 py-3">Rank</th>
                  <th className="px-4 py-3">Model</th>
                  {leaderboard.entries[0]?.metrics && Object.keys(leaderboard.entries[0].metrics).map(m => (
                    <th key={m} className={`px-4 py-3 ${m === leaderboard.primary_metric ? 'text-sky-400' : ''}`}>
                      {m.toUpperCase()}
                    </th>
                  ))}
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {leaderboard.entries.map((entry: any, idx: number) => (
                  <tr key={entry.experiment_id || entry.algorithm}
                    className={`animate-fade-in-up stagger-${idx + 1} hover:bg-slate-800/20 transition-colors ${
                      idx === 0 ? 'bg-amber-500/[0.03]' : ''
                    }`}>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center justify-center w-8 h-8 rounded-xl text-xs font-bold ${
                        entry.rank === 1 ? 'bg-gradient-to-br from-amber-500/30 to-yellow-500/20 text-amber-300 border border-amber-500/30 shadow-sm shadow-amber-500/10' :
                        entry.rank === 2 ? 'bg-slate-500/15 text-slate-300 border border-slate-500/20' :
                        entry.rank === 3 ? 'bg-orange-500/10 text-orange-300 border border-orange-500/20' :
                        'bg-slate-800/50 text-slate-400'
                      }`}>
                        {entry.rank === 1 ? '🏆' : entry.rank}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="font-semibold text-slate-200">{entry.display_name || entry.algorithm}</span>
                    </td>
                    {entry.metrics && Object.entries(entry.metrics).map(([key, val]: [string, any]) => (
                      <td key={key} className={`px-4 py-3.5 font-mono text-xs ${
                        key === leaderboard.primary_metric ? 'text-sky-400 font-bold text-sm' : ''
                      }`}>
                        {typeof val === 'number' ? val.toFixed(4) : val}
                      </td>
                    ))}
                    <td className="px-4 py-3.5 text-xs text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {entry.training_duration?.toFixed(1)}s
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {entry.experiment_id && (
                        <button onClick={() => registerModel(entry.experiment_id)}
                          className="text-xs px-3 py-1.5 bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-lg hover:bg-sky-500/20 transition-colors font-medium">
                          Register
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Successive Halving Survival Funnel */}
      {funnelData.length > 0 && (
        <div className="animate-fade-in-up glass-card border border-purple-500/20 rounded-2xl p-6 relative overflow-hidden bg-gradient-to-b from-slate-900/90 to-slate-950/90">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-bold text-slate-100">Budget AutoML Successive Halving Funnel</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {funnelData.map((stage, i) => (
              <div key={i} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">{stage.stage}</span>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-400">Candidates Evaluated:</span>
                    <span className="text-sm font-mono font-bold text-slate-200">{stage.models_evaluated}</span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-slate-400">Survived to Next:</span>
                    <span className="text-sm font-mono font-bold text-emerald-400">{stage.models_survived}</span>
                  </div>
                </div>
                <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] text-slate-500 font-mono text-right">
                  {stage.time_elapsed_s}s elapsed
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Experiment History */}
      {experiments.length > 0 && (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-400" /> Experiment History & Reproducibility Export
          </h3>
          <div className="space-y-2.5">
            {experiments.map((exp: any, idx: number) => (
              <div key={exp.id}
                className={`animate-fade-in-up stagger-${Math.min(idx + 1, 8)} flex items-center justify-between p-4 rounded-xl bg-slate-900/40 hover:bg-slate-800/30 transition-all border border-slate-800/30 flex-wrap gap-2`}>
                <div>
                  <p className="text-sm text-slate-300 font-medium">{exp.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{exp.algorithm} • {exp.task_type}</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {exp.metrics && exp.primary_metric && (
                    <span className="text-sm font-mono text-sky-400 font-semibold px-2 py-1 rounded bg-slate-900 border border-slate-800">
                      {exp.primary_metric}: {exp.metrics[exp.primary_metric]?.toFixed(4)}
                    </span>
                  )}
                  <span className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold ${
                    exp.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    exp.status === 'RUNNING' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse' :
                    exp.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                    'bg-slate-700 text-slate-400'
                  }`}>
                    {exp.status}
                  </span>

                  {/* Export Buttons */}
                  {exp.status === 'COMPLETED' && (
                    <div className="flex items-center gap-1.5 ml-2">
                      <a
                        href={`http://localhost:8000/api/experiments/${exp.id}/export?format=notebook`}
                        download={`pipeline_${exp.id.slice(0,8)}.ipynb`}
                        className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/30 flex items-center gap-1 transition-colors"
                        title="Export as Jupyter Notebook"
                      >
                        <Download className="w-3 h-3" /> .ipynb
                      </a>
                      <a
                        href={`http://localhost:8000/api/experiments/${exp.id}/export?format=script`}
                        download={`pipeline_${exp.id.slice(0,8)}.py`}
                        className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/30 flex items-center gap-1 transition-colors"
                        title="Export as Python Script"
                      >
                        <FileCode className="w-3 h-3" /> .py
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!leaderboard && experiments.length === 0 && !loading && (
        <div className="animate-fade-in-up glass-card border border-slate-800/50 rounded-2xl p-16 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto">
            <FlaskConical className="w-8 h-8 text-purple-400" />
          </div>
          <h3 className="text-xl font-bold text-slate-200">No Experiments Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Select a dataset, choose a target column, and start training to see your models compete on the leaderboard
          </p>
          <div className="flex items-center justify-center gap-2 text-purple-400">
            <ArrowRight className="w-4 h-4" />
            <span className="text-sm font-medium">Configure training above to get started</span>
          </div>
        </div>
      )}
    </div>
  );
};
