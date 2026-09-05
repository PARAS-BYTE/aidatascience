import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import {
  Database, FlaskConical, Box, Rocket, Sparkles, ArrowRight, Activity,
  TrendingUp, Zap, BarChart3
} from 'lucide-react';

// Animated counter hook
function useCountUp(end: number, duration: number = 1200) {
  const [count, setCount] = useState(0);
  const ref = useRef<number>(0);

  useEffect(() => {
    if (end === 0) { setCount(0); return; }
    const startTime = performance.now();
    const startVal = ref.current;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startVal + (end - startVal) * eased);
      setCount(current);
      if (progress < 1) requestAnimationFrame(tick);
      else ref.current = end;
    };

    requestAnimationFrame(tick);
  }, [end, duration]);

  return count;
}

// Skeleton card for loading
const SkeletonCard = () => (
  <div className="glass-card rounded-2xl p-5 shadow-xl">
    <div className="flex items-center justify-between">
      <div className="space-y-3 flex-1">
        <div className="skeleton skeleton-text w-20" />
        <div className="skeleton skeleton-title w-16 h-8" />
      </div>
      <div className="skeleton w-12 h-12 rounded-xl" />
    </div>
  </div>
);

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiService.getDashboard().then(setStats).catch(() => setStats(null)).finally(() => setLoading(false));
  }, []);

  const datasetCount = useCountUp(stats?.datasets ?? 0);
  const experimentCount = useCountUp(stats?.experiments ?? 0);
  const modelCount = useCountUp(stats?.models ?? 0);
  const deployedCount = useCountUp(stats?.deployed_models ?? 0);

  const cards = [
    {
      label: 'Datasets', value: datasetCount, rawValue: stats?.datasets ?? 0,
      icon: Database, color: 'sky', link: '/datasets',
      gradient: 'from-sky-500/10 to-blue-500/5',
      borderGlow: 'hover:border-sky-500/30',
      iconBg: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    },
    {
      label: 'Experiments', value: experimentCount, rawValue: stats?.experiments ?? 0,
      icon: FlaskConical, color: 'purple', link: '/experiments',
      gradient: 'from-purple-500/10 to-pink-500/5',
      borderGlow: 'hover:border-purple-500/30',
      iconBg: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    },
    {
      label: 'Models', value: modelCount, rawValue: stats?.models ?? 0,
      icon: Box, color: 'emerald', link: '/models',
      gradient: 'from-emerald-500/10 to-teal-500/5',
      borderGlow: 'hover:border-emerald-500/30',
      iconBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    },
    {
      label: 'Deployed', value: deployedCount, rawValue: stats?.deployed_models ?? 0,
      icon: Rocket, color: 'amber', link: '/deployments',
      gradient: 'from-amber-500/10 to-orange-500/5',
      borderGlow: 'hover:border-amber-500/30',
      iconBg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-2 mb-1">
          <Zap className="w-5 h-5 text-sky-400" />
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">Platform Overview</span>
        </div>
        <h1 className="text-3xl font-black text-slate-100 tracking-tight">
          AI Data Scientist Platform
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          End-to-end AutoML with deterministic computation and AI orchestration
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          cards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <Link
                key={card.label}
                to={card.link}
                className={`animate-fade-in-up stagger-${idx + 1} glass-card rounded-2xl p-5 shadow-xl card-hover border border-slate-800/50 ${card.borderGlow} transition-all group relative overflow-hidden`}
              >
                {/* Gradient overlay */}
                <div className={`absolute inset-0 bg-gradient-to-br ${card.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl`} />

                <div className="relative z-10 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 group-hover:text-slate-300 transition-colors">
                      {card.label}
                    </p>
                    <h3 className="text-3xl font-black text-slate-100 mt-2 animate-count-up">
                      {card.value}
                    </h3>
                    {card.rawValue > 0 && (
                      <div className="flex items-center gap-1 mt-1">
                        <TrendingUp className="w-3 h-3 text-emerald-400" />
                        <span className="text-[10px] text-emerald-400 font-medium">Active</span>
                      </div>
                    )}
                  </div>
                  <div className={`p-3 rounded-xl border ${card.iconBg} group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className="w-6 h-6" />
                  </div>
                </div>
              </Link>
            );
          })
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Link
          to="/datasets"
          className="animate-fade-in-up stagger-5 glass-card rounded-2xl p-6 flex items-center justify-between gap-4 border border-slate-800/50 hover:border-sky-500/30 transition-all group card-hover relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-sky-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <div className="space-y-1 relative z-10">
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Database className="w-4 h-4 text-sky-400" /> Upload Dataset
            </h3>
            <p className="text-sm text-slate-400">Start by uploading a CSV/XLSX dataset for analysis</p>
          </div>
          <ArrowRight className="w-5 h-5 text-sky-400 shrink-0 group-hover:translate-x-1 transition-transform" />
        </Link>
        <Link
          to="/ai-chat"
          className="animate-fade-in-up stagger-6 glass-card rounded-2xl p-6 flex items-center justify-between gap-4 border border-slate-800/50 hover:border-purple-500/30 transition-all group card-hover relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <div className="space-y-1 relative z-10">
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" /> AI Data Scientist
            </h3>
            <p className="text-sm text-slate-400">Ask questions about your data in natural language</p>
          </div>
          <ArrowRight className="w-5 h-5 text-purple-400 shrink-0 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Datasets */}
        <div className="animate-fade-in-up stagger-7 glass-card border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Database className="w-4 h-4 text-sky-400" /> Recent Datasets
          </h3>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg">
                  <div className="skeleton skeleton-text w-40" />
                  <div className="skeleton skeleton-text w-20" />
                </div>
              ))}
            </div>
          ) : stats?.recent_datasets?.length > 0 ? (
            <div className="space-y-1">
              {stats.recent_datasets.map((d: any, idx: number) => (
                <Link
                  key={d.id}
                  to={`/datasets/${d.id}`}
                  className={`animate-fade-in-up stagger-${idx + 1} flex items-center justify-between p-3 rounded-xl hover:bg-slate-800/30 transition-all group`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                      <BarChart3 className="w-4 h-4 text-sky-400" />
                    </div>
                    <span className="text-sm text-slate-300 group-hover:text-slate-100 transition-colors truncate">
                      {d.name}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">
                    {new Date(d.created_at).toLocaleDateString()}
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Database className="w-10 h-10 text-slate-700 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No datasets uploaded yet</p>
              <Link to="/datasets" className="text-xs text-sky-400 hover:text-sky-300 mt-1 inline-block">
                Upload your first dataset →
              </Link>
            </div>
          )}
        </div>

        {/* Recent Experiments */}
        <div className="animate-fade-in-up stagger-8 glass-card border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" /> Recent Experiments
          </h3>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg">
                  <div className="space-y-1">
                    <div className="skeleton skeleton-text w-36" />
                    <div className="skeleton skeleton-text w-24" />
                  </div>
                  <div className="skeleton w-20 h-6 rounded-full" />
                </div>
              ))}
            </div>
          ) : stats?.recent_experiments?.length > 0 ? (
            <div className="space-y-1">
              {stats.recent_experiments.map((e: any, idx: number) => (
                <div
                  key={e.id}
                  className={`animate-fade-in-up stagger-${idx + 1} flex items-center justify-between p-3 rounded-xl bg-slate-800/20 hover:bg-slate-800/40 transition-all`}
                >
                  <div>
                    <span className="text-sm text-slate-300 block truncate max-w-xs">{e.name}</span>
                    <span className="text-xs text-slate-500">{e.algorithm}</span>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                    e.status === 'COMPLETED'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : e.status === 'RUNNING'
                      ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                      : e.status === 'FAILED'
                      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      : 'bg-slate-700 text-slate-400'
                  }`}>
                    {e.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FlaskConical className="w-10 h-10 text-slate-700 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No experiments yet</p>
              <Link to="/experiments" className="text-xs text-purple-400 hover:text-purple-300 mt-1 inline-block">
                Train your first model →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
