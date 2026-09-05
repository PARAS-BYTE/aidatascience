import React from 'react';
import {
  CheckCircle2, Clock, XCircle, ShieldCheck,
  Cpu, Activity, Database, BarChart3, Brain, Layers
} from 'lucide-react';

export interface DAGNodeInfo {
  node_id: string;
  agent_name: string;
  display_name: string;
  description?: string;
  category: string;
  dependencies: string[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'validated' | 'skipped';
  duration_ms?: number;
  error?: string;
  critic_review?: {
    passed: boolean;
    score: number;
    comments: string;
  };
}

interface MultiAgentDAGVisualizerProps {
  nodes: DAGNodeInfo[];
  totalDurationMs?: number;
  activeIntent?: string;
}

export const MultiAgentDAGVisualizer: React.FC<MultiAgentDAGVisualizerProps> = ({
  nodes,
  totalDurationMs,
  activeIntent,
}) => {
  // Group nodes by category
  const categories = [
    { key: 'understanding', label: '1. Data Understanding (Parallel Upload Layer)', icon: Database, color: 'text-sky-400 bg-sky-500/10 border-sky-500/20' },
    { key: 'analysis', label: '2. Analytics & Trend Engines (Parallel Execution)', icon: BarChart3, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
    { key: 'ml', label: '3. Machine Learning Specialists (AutoML Fan-out)', icon: Brain, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
    { key: 'dashboard', label: '4. Power BI Dashboard Layout Layer', icon: Layers, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
    { key: 'critic', label: '5. Critic & Validator Layer (QA Audit)', icon: ShieldCheck, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'running':
        return <Activity className="w-4 h-4 text-sky-400 animate-spin shrink-0" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-rose-400 shrink-0" />;
      case 'validated':
        return <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />;
      default:
        return <Clock className="w-4 h-4 text-slate-500 shrink-0" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'running':
        return 'bg-sky-500/20 text-sky-300 border-sky-500/40 animate-pulse';
      case 'failed':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default:
        return 'bg-slate-800 text-slate-500 border-slate-700';
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 text-white shadow-md shadow-sky-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>Multi-Agent Task Graph (DAG)</span>
              {activeIntent && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-sky-400 border border-slate-700 font-mono">
                  Intent: {activeIntent}
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400">Concurrent specialized agents executing in parallel via task graph</p>
          </div>
        </div>

        {totalDurationMs !== undefined && (
          <div className="text-right">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Total Execution Latency</span>
            <div className="text-sm font-mono font-bold text-sky-400">{totalDurationMs} ms</div>
          </div>
        )}
      </div>

      {/* Categories & Agent Nodes */}
      <div className="space-y-5">
        {categories.map(cat => {
          const categoryNodes = nodes.filter(n => n.category === cat.key);
          if (categoryNodes.length === 0) return null;

          const Icon = cat.icon;

          return (
            <div key={cat.key} className="space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                <span className={`p-1 rounded-lg border ${cat.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </span>
                <span>{cat.label}</span>
                <span className="text-[10px] text-slate-500 font-mono">({categoryNodes.length} agents)</span>
              </div>

              {/* Agent Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {categoryNodes.map(node => (
                  <div
                    key={node.node_id}
                    className={`p-3.5 rounded-xl border transition-all ${
                      node.status === 'running'
                        ? 'bg-sky-950/30 border-sky-500/50 shadow-lg shadow-sky-500/10 scale-[1.01]'
                        : node.status === 'completed'
                        ? 'bg-slate-800/60 border-slate-700/80 hover:border-slate-600'
                        : 'bg-slate-900/40 border-slate-800/60 opacity-60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(node.status)}
                        <div>
                          <h4 className="text-xs font-bold text-slate-200">{node.display_name}</h4>
                          <span className="text-[10px] text-slate-500 font-mono">{node.agent_name}</span>
                        </div>
                      </div>

                      <span className={`text-[10px] px-2 py-0.5 rounded-md border font-semibold capitalize ${getStatusBadge(node.status)}`}>
                        {node.status}
                      </span>
                    </div>

                    {node.description && (
                      <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">{node.description}</p>
                    )}

                    {/* Node Footer: Duration & Dependencies */}
                    <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>
                        {node.duration_ms ? `${node.duration_ms}ms` : (node.status === 'running' ? 'Executing...' : 'Waiting')}
                      </span>

                      {node.dependencies.length > 0 ? (
                        <span className="text-slate-400">
                          Depends on: {node.dependencies.join(', ')}
                        </span>
                      ) : (
                        <span className="text-sky-400/80">Parallel Fan-out</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
