import React from 'react';
import { X, Sparkles } from 'lucide-react';
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export interface DriverItem {
  dimension_value: string;
  sum_contribution: number;
  share_percentage: number;
  mean_value: number;
  delta_vs_average_pct: number;
  driver_type: 'Positive Driver' | 'Negative Driver' | 'Neutral Baseline';
}

export interface DimensionBreakdown {
  dimension: string;
  primary_positive_driver: string;
  primary_negative_driver: string;
  drivers: DriverItem[];
}

export interface WhyAnalysisResult {
  target_metric: string;
  overall_total: number;
  overall_mean: number;
  dimension_breakdowns: DimensionBreakdown[];
  top_root_cause_summary: string;
}

interface WhyInvestigationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  data: WhyAnalysisResult | null;
  isLoading: boolean;
}

export const WhyInvestigationDrawer: React.FC<WhyInvestigationDrawerProps> = ({
  isOpen,
  onClose,
  data,
  isLoading,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col p-6 overflow-y-auto space-y-6 animate-slide-left">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Root-Cause Investigation ("Why?")</h2>
              <p className="text-xs text-slate-400">Parallel multi-dimensional variance decomposition</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-3 py-16">
            <div className="w-8 h-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            <p className="text-xs text-slate-400">Running parallel dimension decomposition across sub-agents...</p>
          </div>
        ) : !data ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No investigation data available.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Executive Summary Card */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-sky-950/40 via-indigo-950/20 to-slate-900 border border-sky-500/30 space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400">Primary Finding</span>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {data.top_root_cause_summary}
              </p>
              <div className="flex items-center gap-4 pt-2 text-[11px] text-slate-400 font-mono">
                <span>Metric: <strong>{data.target_metric}</strong></span>
                <span>Dataset Avg: <strong>{data.overall_mean}</strong></span>
                <span>Total Volume: <strong>{data.overall_total}</strong></span>
              </div>
            </div>

            {/* Dimension Breakdown Cards */}
            <div className="space-y-6">
              {data.dimension_breakdowns.map(dim => {
                const chartData = dim.drivers.slice(0, 6).map(d => ({
                  name: d.dimension_value,
                  delta: d.delta_vs_average_pct,
                  share: d.share_percentage,
                }));

                return (
                  <div key={dim.dimension} className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                          Dimension: {dim.dimension}
                        </h3>
                        <p className="text-[11px] text-slate-400">
                          Top Positive: <strong className="text-emerald-400">{dim.primary_positive_driver}</strong> • Top Negative: <strong className="text-rose-400">{dim.primary_negative_driver}</strong>
                        </p>
                      </div>
                    </div>

                    {/* Variance Deviation Chart */}
                    <div className="h-44 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                          <XAxis type="number" stroke="#94a3b8" fontSize={10} unit="%" />
                          <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={80} />
                          <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem' }} />
                          <Bar dataKey="delta" radius={[0, 4, 4, 0]}>
                            {chartData.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={entry.delta >= 0 ? '#34d399' : '#f87171'}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Driver List Pills */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-700/40">
                      {dim.drivers.slice(0, 4).map(drv => (
                        <div key={drv.dimension_value} className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] flex items-center justify-between">
                          <span className="font-semibold text-slate-300">{drv.dimension_value}</span>
                          <span className={drv.delta_vs_average_pct >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                            {drv.delta_vs_average_pct >= 0 ? `+${drv.delta_vs_average_pct}%` : `${drv.delta_vs_average_pct}%`}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
