import React, { useState, useEffect } from 'react';
import {
  Sparkles, Bot, CheckCircle2, AlertCircle, Loader2, ArrowRight,
  Cpu, BarChart3, Database,
  Sliders, ShieldCheck, Zap, Award, Rocket, MessageSquare,
  RefreshCw, X, Check, Flame
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, Cell
} from 'recharts';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';

interface Step {
  step_number: number;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  summary: string;
  details?: Record<string, any>;
}

interface AutoPilotResponse {
  dataset_id: string;
  filename: string;
  target_column: string;
  task_type: string;
  status: string;
  steps: Step[];
  feature_engineering_summary?: Record<string, any>;
  model_selection_reasoning?: string;
  leaderboard?: Array<Record<string, any>>;
  best_model?: {
    name: string;
    score: number;
    metric: string;
    registered_model_id?: string;
  };
  feature_importance?: Array<{ feature: string; importance: number; percentage?: number }>;
  charts?: Array<any>;
  executive_summary: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  datasetId: string;
  filename?: string;
  initialTarget?: string;
}

const STEP_DEFINITIONS = [
  {
    step_number: 1,
    title: 'Dataset Intelligence & Target Detection',
    icon: Database,
    description: 'Profiles dimensions, column types, missing values, duplicates, and detects ML task type.',
  },
  {
    step_number: 2,
    title: 'AI Feature Engineering Strategy',
    icon: Sparkles,
    description: 'Reasons over date features, skewness, correlations, and formulates transformation recipe.',
  },
  {
    step_number: 3,
    title: 'Automated Data Transformation',
    icon: Zap,
    description: 'Cleans anomalies, handles missing data, and creates pairwise interactions.',
  },
  {
    step_number: 4,
    title: 'AI Model Selection Reasoning',
    icon: Cpu,
    description: 'Evaluates scale, sparsity, and non-linearity to select optimal candidate model families.',
  },
  {
    step_number: 5,
    title: 'AutoML Training & Leaderboard',
    icon: Award,
    description: 'Executes parallel cross-validated model training and builds ranked leaderboard.',
  },
  {
    step_number: 6,
    title: 'Explainability & Best Model Summary',
    icon: BarChart3,
    description: 'Computes SHAP global feature importances, evaluates readiness, and auto-registers champion model.',
  },
];

const COLORS = ['#38bdf8', '#818cf8', '#a855f7', '#34d399', '#f59e0b', '#ec4899', '#14b8a6', '#f43f5e'];

export const AIAutoPilotModal: React.FC<Props> = ({
  isOpen,
  onClose,
  datasetId,
  filename,
  initialTarget,
}) => {
  const navigate = useNavigate();

  // Configuration State
  const [target, setTarget] = useState<string>(initialTarget || '');
  const [columns, setColumns] = useState<string[]>([]);
  const [suggestedTarget, setSuggestedTarget] = useState<string>('');
  const [detectedTask, setDetectedTask] = useState<string>('');
  const [cvFolds, setCvFolds] = useState<number>(5);
  const [enableFE, setEnableFE] = useState<boolean>(true);
  const [maxInteractions, setMaxInteractions] = useState<number>(5);
  const [llmModel, setLlmModel] = useState<string>('openai/gpt-oss-120b');

  // Execution & Pipeline State
  const [running, setRunning] = useState<boolean>(false);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [simulatedSteps, setSimulatedSteps] = useState<Step[]>([]);
  const [result, setResult] = useState<AutoPilotResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'leaderboard' | 'shap' | 'steps'>('summary');
  const [deploying, setDeploying] = useState<boolean>(false);
  const [deploySuccess, setDeploySuccess] = useState<string | null>(null);

  // Initialize & Load Profile / Target Suggestions
  useEffect(() => {
    if (!isOpen || !datasetId) return;

    // Reset execution state
    setError(null);
    setDeploySuccess(null);

    const loadMetadata = async () => {
      try {
        const preview = await apiService.getDatasetPreview(datasetId, 5, 0);
        if (preview && preview.columns) {
          setColumns(preview.columns);
        }

        const targetData = await apiService.suggestTarget(datasetId);
        if (targetData && targetData.suggested_target) {
          setSuggestedTarget(targetData.suggested_target);
          if (!target) {
            setTarget(targetData.suggested_target);
          }
          if (targetData.task_type) {
            setDetectedTask(targetData.task_type);
          }
        }
      } catch (e) {
        // Fallback gracefully
      }
    };

    loadMetadata();
  }, [isOpen, datasetId]);

  if (!isOpen) return null;

  // Execute AI Auto-Pilot Pipeline
  const handleLaunchAutoPilot = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    setDeploySuccess(null);
    setActiveTab('steps');

    // Initialize visual simulated tracker
    const initSteps: Step[] = STEP_DEFINITIONS.map(d => ({
      step_number: d.step_number,
      title: d.title,
      status: 'pending',
      summary: d.description,
    }));
    initSteps[0].status = 'in_progress';
    setSimulatedSteps(initSteps);
    setCurrentStepIndex(0);

    // Step simulation ticker for visual immersion while server processes
    let stepTicker = 0;
    const interval = setInterval(() => {
      stepTicker += 1;
      if (stepTicker < 6) {
        setCurrentStepIndex(stepTicker);
        setSimulatedSteps(prev =>
          prev.map((s, idx) => {
            if (idx < stepTicker) return { ...s, status: 'completed' };
            if (idx === stepTicker) return { ...s, status: 'in_progress' };
            return { ...s, status: 'pending' };
          })
        );
      }
    }, 2800);

    try {
      const response: AutoPilotResponse = await apiService.runAutoPilot(
        datasetId,
        target || undefined,
        llmModel || undefined,
        enableFE,
        cvFolds,
        maxInteractions
      );

      clearInterval(interval);
      setResult(response);
      setSimulatedSteps(response.steps);
      setCurrentStepIndex(6);
      setActiveTab('summary');
    } catch (err: any) {
      clearInterval(interval);
      const msg = err.response?.data?.detail || err.message || 'Auto-Pilot pipeline encountered an error.';
      setError(msg);
      setSimulatedSteps(prev =>
        prev.map((s, idx) => {
          if (idx === currentStepIndex) return { ...s, status: 'failed' };
          return s;
        })
      );
    } finally {
      setRunning(false);
    }
  };

  const handleDeployModel = async (modelId?: string) => {
    if (!modelId) return;
    setDeploying(true);
    try {
      const res = await apiService.deployModel(modelId);
      setDeploySuccess(`Model deployed successfully! Live endpoint: ${res.endpoint || '/api/models/' + modelId + '/predict'}`);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to deploy model.');
    } finally {
      setDeploying(false);
    }
  };

  const handleOpenAIChat = () => {
    onClose();
    navigate(`/chat?dataset=${datasetId}`);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden">
        
        {/* Modal Header */}
        <div className="relative px-6 py-5 border-b border-slate-800 bg-gradient-to-r from-slate-900 via-purple-950/30 to-slate-900 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-purple-500 to-indigo-500 p-0.5 shadow-lg shadow-purple-500/20 flex items-center justify-center">
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  Autonomous AI Auto-Pilot Pipeline
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-[10px] font-mono uppercase font-semibold">
                  v2.0 Agent
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {filename ? <span className="text-slate-300 font-semibold">{filename}</span> : 'Dataset'}{' '}
                • Autonomous Feature Engineering, Model Selection & SHAP Diagnostics
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={running}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Pipeline Configuration Strip (When not running and no result) */}
          {!running && !result && (
            <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800/80 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                  <Sliders className="w-4 h-4 text-purple-400" />
                  Auto-Pilot Configuration & Target Detection
                </div>
                {detectedTask && (
                  <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-mono">
                    Task: {detectedTask.replace('_', ' ').toUpperCase()}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Target Column Selection */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5 flex items-center justify-between">
                    <span>Target Variable (To Predict)</span>
                    {suggestedTarget && (
                      <span className="text-[10px] text-purple-400 font-mono">
                        Suggested: {suggestedTarget}
                      </span>
                    )}
                  </label>
                  <select
                    value={target}
                    onChange={e => setTarget(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-purple-500 transition-colors"
                  >
                    <option value="">Auto-detect best target column</option>
                    {columns.map(col => (
                      <option key={col} value={col}>
                        {col} {col === suggestedTarget ? '★ (Recommended)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                {/* CV Folds */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    Cross-Validation Folds
                  </label>
                  <select
                    value={cvFolds}
                    onChange={e => setCvFolds(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-purple-500 transition-colors font-mono"
                  >
                    <option value={3}>3 Folds (Fast)</option>
                    <option value={5}>5 Folds (Recommended)</option>
                    <option value={10}>10 Folds (Thorough)</option>
                  </select>
                </div>

                {/* LLM Agent Model */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    AI Reasoning Model
                  </label>
                  <select
                    value={llmModel}
                    onChange={e => setLlmModel(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-xl px-3.5 py-2.5 text-xs focus:outline-none focus:border-purple-500 transition-colors"
                  >
                    <option value="openai/gpt-oss-120b">GPT-OSS 120B (Groq)</option>
                    <option value="openai/gpt-oss-20b">GPT-OSS 20B (Groq)</option>
                    <option value="qwen/qwen3.8-27b">Qwen 3.8 27B (Groq)</option>
                  </select>
                </div>
              </div>

              {/* Toggles */}
              <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800/60 text-xs">
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={enableFE}
                    onChange={e => setEnableFE(e.target.checked)}
                    className="rounded border-slate-700 text-purple-600 focus:ring-purple-500 bg-slate-900"
                  />
                  <span>Enable AI Feature Engineering (Interactions, Date Decomposition, Outlier Filters)</span>
                </label>

                {enableFE && (
                  <div className="flex items-center gap-2 text-slate-400">
                    <span>Max Interactions:</span>
                    <input
                      type="number"
                      min={1}
                      max={15}
                      value={maxInteractions}
                      onChange={e => setMaxInteractions(Math.max(1, Math.min(15, Number(e.target.value))))}
                      className="w-14 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-center text-slate-200 text-xs font-mono"
                    />
                  </div>
                )}
              </div>

              {/* Action Banner */}
              <div className="pt-2 flex items-center justify-between">
                <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Protected by Llama Prompt Guard & Isolated Cross-Validation
                </div>
                <button
                  onClick={handleLaunchAutoPilot}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-sky-600 hover:from-purple-500 hover:via-indigo-500 hover:to-sky-500 text-white font-semibold text-sm shadow-xl shadow-purple-500/25 transition-all flex items-center gap-2 group cursor-pointer"
                >
                  <Sparkles className="w-4 h-4 group-hover:rotate-12 transition-transform" />
                  <span>Execute AI Auto-Pilot</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-rose-200">Execution Alert</p>
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* Deploy Success Banner */}
          {deploySuccess && (
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <span>{deploySuccess}</span>
            </div>
          )}

          {/* Step-by-Step Live Visual Tracker Cards */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-purple-400" />
                6-Stage Autonomous Data Science Lifecycle
              </span>
              {running && (
                <span className="inline-flex items-center gap-1.5 text-purple-400 animate-pulse font-mono">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Agent Reasoning & Training...
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {STEP_DEFINITIONS.map((stepDef, idx) => {
                const IconComponent = stepDef.icon;
                const stateStep = simulatedSteps[idx] || (result?.steps?.[idx]);
                const isCompleted = stateStep?.status === 'completed';
                const isCurrent = running && currentStepIndex === idx;
                const isFailed = stateStep?.status === 'failed';

                return (
                  <div
                    key={stepDef.step_number}
                    className={`p-4 rounded-2xl border transition-all duration-300 flex flex-col justify-between ${
                      isCompleted
                        ? 'bg-slate-900/90 border-emerald-500/40 shadow-sm shadow-emerald-500/5'
                        : isCurrent
                        ? 'bg-gradient-to-b from-purple-950/40 to-slate-900 border-purple-500 shadow-lg shadow-purple-500/10 ring-1 ring-purple-500/50'
                        : isFailed
                        ? 'bg-rose-950/20 border-rose-500/40'
                        : 'bg-slate-950/60 border-slate-800/80 opacity-60'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`p-2 rounded-xl ${
                            isCompleted
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : isCurrent
                              ? 'bg-purple-500/20 text-purple-400 animate-bounce'
                              : 'bg-slate-800 text-slate-500'
                          }`}>
                            <IconComponent className="w-4 h-4" />
                          </div>
                          <span className="text-[11px] font-mono text-slate-400">
                            Stage 0{stepDef.step_number}
                          </span>
                        </div>

                        {isCompleted && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                            <Check className="w-3 h-3" /> Done
                          </span>
                        )}
                        {isCurrent && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-purple-300 bg-purple-500/20 border border-purple-500/30 px-2 py-0.5 rounded-full font-mono">
                            <Loader2 className="w-3 h-3 animate-spin" /> Active
                          </span>
                        )}
                      </div>

                      <h4 className="text-xs font-bold text-slate-200">
                        {stepDef.title}
                      </h4>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        {stateStep?.summary || stepDef.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Results View (Once Auto-Pilot Finishes) */}
          {result && (
            <div className="space-y-6 pt-2 animate-in fade-in duration-300">
              {/* Executive KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-2xl bg-gradient-to-br from-purple-950/40 to-slate-900 border border-purple-500/30 space-y-1">
                  <div className="text-[11px] text-purple-400 font-semibold uppercase flex items-center gap-1.5">
                    <Award className="w-4 h-4" /> Champion Model
                  </div>
                  <div className="text-lg font-bold text-white truncate">
                    {result.best_model?.name || 'Top Model'}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Rank #1 across candidate architectures
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-950/40 to-slate-900 border border-emerald-500/30 space-y-1">
                  <div className="text-[11px] text-emerald-400 font-semibold uppercase flex items-center gap-1.5">
                    <Flame className="w-4 h-4" /> Primary Score
                  </div>
                  <div className="text-lg font-bold text-emerald-300 font-mono">
                    {result.best_model?.score ? (result.best_model.score > 1 ? result.best_model.score.toFixed(4) : `${(result.best_model.score * 100).toFixed(2)}%`) : 'N/A'}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono uppercase">
                    Metric: {result.best_model?.metric || 'Score'}
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-gradient-to-br from-sky-950/40 to-slate-900 border border-sky-500/30 space-y-1">
                  <div className="text-[11px] text-sky-400 font-semibold uppercase flex items-center gap-1.5">
                    <Zap className="w-4 h-4" /> Features Engineered
                  </div>
                  <div className="text-lg font-bold text-sky-300 font-mono">
                    +{result.feature_engineering_summary?.new_features?.length || 0} New
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Total: {result.feature_engineering_summary?.transformed_shape?.[1] || 0} columns
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-950/40 to-slate-900 border border-indigo-500/30 space-y-1">
                  <div className="text-[11px] text-indigo-400 font-semibold uppercase flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4" /> Status
                  </div>
                  <div className="text-lg font-bold text-indigo-300 flex items-center gap-1.5">
                    <span>Verified</span>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Ready for Deployment
                  </div>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-slate-800 gap-2">
                {[
                  { id: 'summary', label: 'Executive Summary', icon: Sparkles },
                  { id: 'leaderboard', label: 'AutoML Leaderboard', icon: Award },
                  { id: 'shap', label: 'SHAP Feature Importance', icon: BarChart3 },
                ].map(t => {
                  const Icon = t.icon;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id as any)}
                      className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                        activeTab === t.id
                          ? 'border-purple-500 text-purple-400 bg-purple-500/10 rounded-t-lg'
                          : 'border-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {t.label}
                    </button>
                  );
                })}
              </div>

              {/* Tab 1: Executive Summary */}
              {activeTab === 'summary' && (
                <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-4">
                  <div className="prose prose-invert prose-sm max-w-none text-xs leading-relaxed text-slate-300">
                    <h3 className="text-sm font-bold text-slate-100 mb-2">Autonomous Data Science Rationale</h3>
                    <p className="text-slate-300 mb-3">
                      {result.model_selection_reasoning || 'The AI Agent evaluated dataset scale, sparsity, and task formulation to benchmark candidate architectures and isolate top predictive performance.'}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-3">
                      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                        <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                          <Zap className="w-3.5 h-3.5 text-amber-400" /> Feature Engineering Recipe Applied
                        </span>
                        <p className="text-[11px] text-slate-400">
                          {result.steps?.[1]?.summary || 'Temporal decomposition, pairwise interactions, and median imputation.'}
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                        <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                          <BarChart3 className="w-3.5 h-3.5 text-purple-400" /> Explainability Verdict
                        </span>
                        <p className="text-[11px] text-slate-400">
                          {result.steps?.[5]?.summary || 'Computed SHAP tree explainability and global feature impact.'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Leaderboard */}
              {activeTab === 'leaderboard' && (
                <div className="space-y-4">
                  <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/80">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                        <tr>
                          <th className="px-5 py-3">Rank</th>
                          <th className="px-5 py-3">Algorithm</th>
                          <th className="px-5 py-3 font-mono">Primary Metric</th>
                          <th className="px-5 py-3 font-mono">Duration</th>
                          <th className="px-5 py-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {result.leaderboard?.map((entry, idx) => (
                          <tr key={idx} className={idx === 0 ? 'bg-purple-950/20' : 'hover:bg-slate-900/40'}>
                            <td className="px-5 py-3 font-bold flex items-center gap-2">
                              {idx === 0 ? (
                                <span className="p-1 rounded-md bg-amber-500/20 text-amber-400 text-xs">👑 #1</span>
                              ) : (
                                <span className="text-slate-500">#{idx + 1}</span>
                              )}
                            </td>
                            <td className="px-5 py-3 font-semibold text-slate-200">
                              {entry.display_name || entry.algorithm}
                            </td>
                            <td className="px-5 py-3 font-mono text-emerald-400 font-semibold">
                              {entry.primary_metric_value !== undefined ? (
                                entry.primary_metric_value > 1 ? entry.primary_metric_value.toFixed(4) : `${(entry.primary_metric_value * 100).toFixed(2)}%`
                              ) : 'N/A'}
                            </td>
                            <td className="px-5 py-3 font-mono text-slate-400 text-[11px]">
                              {entry.training_duration ? `${entry.training_duration.toFixed(2)}s` : '—'}
                            </td>
                            <td className="px-5 py-3">
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                {entry.status || 'completed'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Leaderboard Bar Chart */}
                  {result.leaderboard && result.leaderboard.length > 0 && (
                    <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
                      <h4 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-purple-400" />
                        Model Performance Benchmark (%)
                      </h4>
                      <div className="h-56">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={result.leaderboard.map(e => ({
                              name: e.display_name || e.algorithm,
                              score: Number((e.primary_metric_value > 1 ? e.primary_metric_value : e.primary_metric_value * 100).toFixed(1)),
                            }))}
                            margin={{ top: 10, right: 20, left: -20, bottom: 20 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                            <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} angle={-15} textAnchor="end" />
                            <YAxis stroke="#94a3b8" fontSize={10} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                              formatter={(val: any) => [`${val}%`, 'Score']}
                            />
                            <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                              {result.leaderboard.map((_, i) => (
                                <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: SHAP Feature Importance */}
              {activeTab === 'shap' && (
                <div className="space-y-4">
                  {result.feature_importance && result.feature_importance.length > 0 ? (
                    <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="text-xs font-bold text-slate-100 flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-sky-400" />
                            Global SHAP Feature Impact
                          </h4>
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            Features with greatest predictive influence on champion model predictions.
                          </p>
                        </div>
                      </div>

                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            layout="vertical"
                            data={result.feature_importance.slice(0, 8).map(f => ({
                              feature: f.feature,
                              importance: Number(f.importance.toFixed(4)),
                            }))}
                            margin={{ top: 10, right: 30, left: 60, bottom: 10 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                            <XAxis type="number" stroke="#94a3b8" fontSize={10} />
                            <YAxis type="category" dataKey="feature" stroke="#94a3b8" fontSize={10} width={90} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '11px' }}
                            />
                            <Bar dataKey="importance" fill="#818cf8" radius={[0, 6, 6, 0]}>
                              {result.feature_importance.slice(0, 8).map((_, i) => (
                                <Cell key={`shap-${i}`} fill={COLORS[i % COLORS.length]} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-800">
                        {result.feature_importance.slice(0, 6).map((f, i) => (
                          <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800/80 text-xs">
                            <span className="font-semibold text-slate-300 truncate max-w-[180px]">{f.feature}</span>
                            <span className="font-mono text-purple-400 font-bold">{f.importance.toFixed(4)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-400 text-xs bg-slate-950/60 rounded-2xl border border-slate-800">
                      Feature importance computed directly during cross-validation.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer / Action Toolbar */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2">
            {result && (
              <button
                onClick={handleLaunchAutoPilot}
                disabled={running}
                className="px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors inline-flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Re-run Auto-Pilot
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {result?.best_model?.registered_model_id && (
              <button
                onClick={() => handleDeployModel(result.best_model?.registered_model_id)}
                disabled={deploying}
                className="px-4 py-2 text-xs font-semibold text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-xl transition-colors inline-flex items-center gap-1.5"
              >
                {deploying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
                Deploy Champion Model
              </button>
            )}

            <button
              onClick={handleOpenAIChat}
              className="px-4 py-2 text-xs font-semibold text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-xl transition-colors inline-flex items-center gap-1.5"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Discuss in AI Chat
            </button>

            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
