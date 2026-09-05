import React, { useState, useEffect } from 'react';
import {
  Sparkles, Send, Cpu, Layers, BarChart3, Search, TrendingUp, Target,
  ShieldCheck, Database, Activity, PieChart, FileText, BrainCircuit
} from 'lucide-react';
import { apiService } from '../services/api';
import { PowerBIDashboard, DashboardSpec } from '../components/dashboard/PowerBIDashboard';
import { MultiAgentDAGVisualizer, DAGNodeInfo } from '../components/dashboard/MultiAgentDAGVisualizer';
import { WhyInvestigationDrawer, WhyAnalysisResult } from '../components/dashboard/WhyInvestigationDrawer';

export const MultiAgentStudio: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [sessionId] = useState<string>(() => `session_${Date.now()}`);
  
  const [prompt, setPrompt] = useState<string>('');
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'dag' | 'blackboard' | 'critic' | 'timeline' | 'plugins'>('dashboard');

  // Multi-agent state
  const [dagNodes, setDagNodes] = useState<DAGNodeInfo[]>([]);
  const [totalDurationMs, setTotalDurationMs] = useState<number | undefined>(undefined);
  const [activeIntent, setActiveIntent] = useState<string>('');
  const [dashboardSpec, setDashboardSpec] = useState<DashboardSpec | null>(null);
  const [blackboardSnapshot, setBlackboardSnapshot] = useState<any>(null);
  const [criticReviews, setCriticReviews] = useState<any[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [plugins, setPlugins] = useState<any[]>([]);
  const [reviewNote, setReviewNote] = useState<string>('');

  const fetchTimeline = async () => {
    try {
      const data = await apiService.getBlackboardTimeline(sessionId);
      if (Array.isArray(data)) {
        setTimelineEvents(data);
      }
    } catch (err) {
      // session may not have events yet
    }
  };

  const fetchPlugins = async () => {
    try {
      const list = await apiService.getPlugins();
      if (Array.isArray(list)) {
        setPlugins(list);
      }
    } catch (err) {
      console.error('Failed to load plugins:', err);
    }
  };

  const handleReview = async (eventId: string, status: 'approved' | 'rejected') => {
    try {
      await apiService.reviewBlackboardEvent(sessionId, eventId, {
        status,
        edited_payload: reviewNote ? { notes: reviewNote } : undefined,
      });
      setReviewNote('');
      fetchTimeline();
    } catch (err) {
      console.error('Review gate update failed:', err);
    }
  };

  // "Why" Investigation state
  const [isWhyDrawerOpen, setIsWhyDrawerOpen] = useState<boolean>(false);
  const [whyData, setWhyData] = useState<WhyAnalysisResult | null>(null);
  const [isWhyLoading, setIsWhyLoading] = useState<boolean>(false);

  // Load datasets on mount
  useEffect(() => {
    apiService.getDatasets().then((data) => {
      const list = Array.isArray(data) ? data : data?.items || [];
      setDatasets(list);
      if (list.length > 0) {
        setSelectedDatasetId(list[0].id);
      }
    }).catch(console.error);
    fetchPlugins();
  }, []);

  const runMultiAgentPipeline = async (userPrompt: string) => {
    if (!selectedDatasetId) return;

    setIsExecuting(true);
    setPrompt(userPrompt);
    setActiveTab('dashboard'); // Switch to dashboard immediately to see live results

    try {
      // Execute multi-agent chat pipeline
      const response = await apiService.multiAgentChat(
        userPrompt,
        sessionId,
        selectedDatasetId
      );

      if (response) {
        setActiveIntent(response.intent || '');
        if (response.dag) {
          setDagNodes(response.dag.nodes || []);
          setTotalDurationMs(response.dag.total_duration_ms);
        }
        if (response.dashboard_spec) {
          setDashboardSpec(response.dashboard_spec);
        }
        if (response.blackboard) {
          setBlackboardSnapshot(response.blackboard);
        }
        if (response.critic_reviews) {
          setCriticReviews(response.critic_reviews);
        }
      }
    } catch (err) {
      console.error('Pipeline execution error:', err);
    } finally {
      setIsExecuting(false);
      fetchTimeline();
    }
  };

  const handlePromptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim()) {
      runMultiAgentPipeline(prompt.trim());
    }
  };

  const handleDashboardPatch = async (patchPrompt: string) => {
    if (!selectedDatasetId) return;
    setIsExecuting(true);
    try {
      const response = await apiService.patchDashboard(sessionId, selectedDatasetId, patchPrompt);
      if (response?.dashboard_spec) {
        setDashboardSpec(response.dashboard_spec);
      }
    } catch (err) {
      console.error('Patch error:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleOpenWhyInvestigation = async (metric: string, dimension?: string) => {
    if (!selectedDatasetId) return;
    setIsWhyDrawerOpen(true);
    setIsWhyLoading(true);
    try {
      const res = await apiService.runWhyInvestigation(sessionId, selectedDatasetId, metric, dimension);
      setWhyData(res?.why_analysis || null);
    } catch (err) {
      console.error('Why investigation error:', err);
    } finally {
      setIsWhyLoading(false);
    }
  };

  const quickPrompts = [
    { label: 'Bar chart', icon: BarChart3, prompt: 'Plot bar chart of primary metric by top dimension' },
    { label: 'Line trend', icon: TrendingUp, prompt: 'Show line chart trend of primary metric over time' },
    { label: 'Share breakdown', icon: PieChart, prompt: 'Show donut chart of categorical distribution' },
    { label: 'Scatter plot', icon: Target, prompt: 'Show scatter plot of correlation between numerical metrics' },
    { label: 'Distribution', icon: BarChart3, prompt: 'Show histogram distribution of primary metric' },
    { label: 'Executive report', icon: FileText, prompt: 'Analyze dataset, uncover trends and anomalies, and build an executive Power BI dashboard' },
    { label: 'Root cause', icon: Search, prompt: 'Why did the primary metric vary across segments? Run dimension decomposition' },
    { label: 'Model leaderboard', icon: BrainCircuit, prompt: 'Formulate ML task, train candidate models in parallel, and produce leaderboard' },
  ];

  return (
    <div className="space-y-6 pb-12 animate-fade-in">
      {/* Top Banner & Dataset Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl glass-card border border-slate-800/50 shadow-xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20 animate-pulse-glow">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black text-slate-100 tracking-tight">AI Multi-Agent Studio</h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30 font-bold uppercase tracking-wider">
                v2 Parallel DAG
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Coordinated specialist agent team with Shared Blackboard & self-assembling Power BI dashboard
            </p>
          </div>
        </div>

        {/* Dataset dropdown — FIXED: use original_filename */}
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-sky-400 shrink-0" />
          <select
            value={selectedDatasetId}
            onChange={(e) => {
              setSelectedDatasetId(e.target.value);
              setDashboardSpec(null);
              setDagNodes([]);
            }}
            className="bg-slate-900/80 border border-slate-700/60 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-sky-500 transition-colors"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename || d.name || d.filename || 'Unnamed'} ({d.row_count || 0} rows)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Prompt Input Bar */}
      <div className="p-4 rounded-2xl glass-card border border-slate-800/50 shadow-xl space-y-3">
        <form onSubmit={handlePromptSubmit} className="flex items-center gap-3">
          <div className="relative flex-1">
            <Sparkles className="w-4 h-4 text-sky-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Assign a task to the multi-agent team (e.g. 'Analyze sales patterns, identify anomalies, and build an executive report')..."
              className="w-full bg-slate-900/60 border border-slate-700/60 rounded-xl pl-10 pr-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-all"
              disabled={isExecuting}
            />
          </div>

          <button
            type="submit"
            disabled={!prompt.trim() || isExecuting || !selectedDatasetId}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-sky-500/20 transition-all"
          >
            {isExecuting ? (
              <>
                <Activity className="w-4 h-4 animate-spin" />
                <span>Orchestrating...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Run Team</span>
              </>
            )}
          </button>
        </form>

        {/* Quick Intent Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pt-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold shrink-0">Quick Templates:</span>
          {quickPrompts.map((qp, idx) => {
            const Icon = qp.icon;
            return (
            <button
              key={idx}
              onClick={() => {
                setPrompt(qp.prompt);
                runMultiAgentPipeline(qp.prompt);
              }}
              disabled={isExecuting || !selectedDatasetId}
              className="text-[11px] px-3 py-1.5 rounded-lg bg-slate-800/40 hover:bg-slate-800/80 text-slate-300 hover:text-sky-300 border border-slate-700/40 transition-all shrink-0"
            >
              <span className="inline-flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" />{qp.label}</span>
            </button>
            );
          })}
        </div>
      </div>

      {/* Orchestrating Animation */}
      {isExecuting && !dashboardSpec && (
        <div className="animate-fade-in p-8 rounded-2xl glass-card border border-sky-500/20 text-center space-y-5">
          <div className="flex items-center justify-center gap-4">
            {[BarChart3, Search, Cpu, TrendingUp, Target].map((Icon, i) => (
              <div
                key={i}
                className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 animate-bounce-subtle"
                style={{ animationDelay: `${i * 0.2}s` }}
              >
                <Icon className="w-5 h-5" />
              </div>
            ))}
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-200">Multi-Agent Team is Working...</h3>
            <p className="text-xs text-slate-400 mt-1">Specialist agents are analyzing your data and assembling the dashboard</p>
          </div>
          <div className="flex items-center justify-center gap-1.5">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-sky-400 animate-bounce-subtle"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800/50 pb-2">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'dashboard'
              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Live Power BI Dashboard</span>
          {dashboardSpec && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
        </button>

        <button
          onClick={() => setActiveTab('dag')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'dag'
              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Agent Task Graph (DAG)</span>
          {dagNodes.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
              {dagNodes.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('blackboard')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'blackboard'
              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Shared Blackboard Memory</span>
        </button>

        <button
          onClick={() => setActiveTab('critic')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'critic'
              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Critic & Validator Audits</span>
          {criticReviews.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-mono">
              {criticReviews.length}
            </span>
          )}
        </button>

        <button
          onClick={() => {
            setActiveTab('timeline');
            fetchTimeline();
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'timeline'
              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Timeline & Review Gate</span>
          {timelineEvents.some(e => e.status === 'pending_review') && (
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          )}
        </button>

        <button
          onClick={() => {
            setActiveTab('plugins');
            fetchPlugins();
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'plugins'
              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Plugins ({plugins.length})</span>
        </button>
      </div>

      {/* Tab 1: Live Power BI Dashboard */}
      {activeTab === 'dashboard' && (
        <div>
          {dashboardSpec ? (
            <PowerBIDashboard
              spec={dashboardSpec}
              onOpenWhyInvestigation={handleOpenWhyInvestigation}
              onPatchPrompt={handleDashboardPatch}
              isLoading={isExecuting}
            />
          ) : !isExecuting ? (
            <div className="p-16 rounded-2xl glass-card border border-slate-800/50 text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/20 flex items-center justify-center mx-auto animate-float">
                <Layers className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-slate-200">No Active Dashboard Generated Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Pick a template above or type a prompt like <em>"Build an executive sales dashboard"</em> to watch the multi-agent team assemble the report in real time.
              </p>
              <button
                onClick={() => runMultiAgentPipeline('Analyze dataset and generate executive Power BI dashboard')}
                disabled={!selectedDatasetId}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white text-xs font-bold transition-all shadow-lg shadow-sky-500/20 disabled:opacity-50"
              >
                Generate Dashboard Now
              </button>
            </div>
          ) : null}
        </div>
      )}

      {/* Tab 2: Agent Task Graph (DAG) */}
      {activeTab === 'dag' && (
        <MultiAgentDAGVisualizer
          nodes={dagNodes}
          totalDurationMs={totalDurationMs}
          activeIntent={activeIntent}
        />
      )}

      {/* Tab 3: Shared Blackboard Memory Inspector */}
      {activeTab === 'blackboard' && (
        <div className="p-5 rounded-2xl glass-card border border-slate-800/50 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-sky-400" />
              <h3 className="text-sm font-bold text-slate-100">Blackboard State Snapshot</h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Session: {sessionId}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/50 font-mono text-xs text-sky-300 overflow-x-auto max-h-[500px]">
            <pre>{JSON.stringify(blackboardSnapshot || { message: 'Run a multi-agent task to inspect state.' }, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* Tab 4: Critic & Validator Audits */}
      {activeTab === 'critic' && (
        <div className="p-5 rounded-2xl glass-card border border-slate-800/50 shadow-xl space-y-4">
          <div className="flex items-center gap-2 text-emerald-400 text-sm font-bold">
            <ShieldCheck className="w-5 h-5" />
            <span>Critic Agent Quality Audits</span>
          </div>

          <div className="space-y-3">
            {criticReviews.length > 0 ? (
              criticReviews.map((rev, idx) => (
                <div key={idx} className="animate-fade-in-up p-4 rounded-xl bg-slate-800/40 border border-slate-700/40 flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-200">Target: {rev.target_agent}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${rev.passed ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                        {rev.passed ? 'VERIFIED' : 'FLAGGED'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{rev.comments}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">Quality Score</span>
                    <div className="text-sm font-bold text-emerald-400">{rev.score * 100}%</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-xs text-slate-500">
                No Critic audits recorded yet. Run a multi-agent query to see automated verification.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 5: Persistent Blackboard Timeline & Review Gate (A5 & B8) */}
      {activeTab === 'timeline' && (
        <div className="p-5 rounded-2xl glass-card border border-slate-800/50 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sky-400 text-sm font-bold">
              <Activity className="w-5 h-5" />
              <span>Blackboard Event Stream & Human-in-the-Loop Review Gate</span>
            </div>
            <button
              onClick={fetchTimeline}
              className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
            >
              Refresh Events
            </button>
          </div>

          <div className="space-y-3">
            {timelineEvents.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No events recorded for this session yet. Run an agent task to view live blackboard events.
              </div>
            ) : (
              timelineEvents.map((evt: any) => {
                const isPending = evt.status === 'pending_review';
                return (
                  <div
                    key={evt.id}
                    className={`p-4 rounded-xl border transition-all ${
                      isPending
                        ? 'bg-amber-950/20 border-amber-500/40'
                        : 'bg-slate-900/60 border-slate-800/60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-200">
                            Agent: <span className="text-sky-400">{evt.agent_name}</span>
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                            {evt.event_type}
                          </span>
                          <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                            evt.status === 'approved'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : evt.status === 'rejected'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}>
                            {evt.status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">{evt.summary}</p>
                        {evt.payload && (
                          <div className="mt-2 p-2 bg-slate-950 rounded-lg font-mono text-[11px] text-slate-400 overflow-x-auto max-h-28">
                            <pre>{JSON.stringify(evt.payload, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono shrink-0">
                        {evt.created_at ? new Date(evt.created_at).toLocaleTimeString() : ''}
                      </span>
                    </div>

                    {/* Human Review Gate Controls */}
                    {isPending && (
                      <div className="mt-3 pt-3 border-t border-amber-500/20 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                        <input
                          type="text"
                          placeholder="Optional reviewer notes..."
                          value={reviewNote}
                          onChange={(e) => setReviewNote(e.target.value)}
                          className="bg-slate-950 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-slate-200 flex-1 focus:outline-none focus:border-amber-400"
                        />
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleReview(evt.id, 'approved')}
                            className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/20"
                          >
                            Approve Action
                          </button>
                          <button
                            onClick={() => handleReview(evt.id, 'rejected')}
                            className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-all shadow-md shadow-rose-600/20"
                          >
                            Reject Action
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 6: Plugin Marketplace (B9) */}
      {activeTab === 'plugins' && (
        <div className="p-5 rounded-2xl glass-card border border-slate-800/50 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-purple-400 text-sm font-bold">
              <Sparkles className="w-5 h-5" />
              <span>Agent Plugin Registry & Marketplace</span>
            </div>
            <span className="text-xs text-slate-400">{plugins.length} plugins installed</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {plugins.map((p: any) => (
              <div key={p.id} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between space-y-3">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-200">{p.name}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      v{p.version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{p.description}</p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {(p.capabilities || []).map((cap: string) => (
                      <span key={cap} className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 font-mono">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs">
                  <span className={p.is_active ? 'text-emerald-400 font-medium' : 'text-slate-500'}>
                    {p.is_active ? '● Active' : '○ Disabled'}
                  </span>
                  <button
                    onClick={async () => {
                      await apiService.togglePlugin(p.id, !p.is_active);
                      fetchPlugins();
                    }}
                    className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                  >
                    {p.is_active ? 'Disable' : 'Enable'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* "Why" Investigation Drawer */}
      <WhyInvestigationDrawer
        isOpen={isWhyDrawerOpen}
        onClose={() => setIsWhyDrawerOpen(false)}
        data={whyData}
        isLoading={isWhyLoading}
      />
    </div>
  );
};
