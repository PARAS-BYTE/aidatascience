import React, { useState } from 'react';
import {
  TrendingUp, TrendingDown, Filter, Sparkles,
  Download, Layers, X, ArrowUpRight
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, LineChart, Line
} from 'recharts';

export interface KPICardSpec {
  id: string;
  metric_key: string;
  title: string;
  value: number;
  formatted_value: string;
  aggregation?: string;
  delta_percentage: number;
  trend_direction: 'up' | 'down' | 'neutral';
  is_positive: boolean;
  sparkline: number[];
  subtitle?: string;
}

export interface ChartSpec {
  id: string;
  type: string;
  title: string;
  x_axis?: string;
  y_axis?: string;
  x_label?: string;
  y_label?: string;
  metric?: string;
  dimension?: string;
  data: any[];
  color?: string;
  colors?: string[];
}

export interface FilterSpec {
  column: string;
  title: string;
  type: string;
  options: string[];
  selected: string[];
}

export interface DashboardSpec {
  layout: string;
  title: string;
  subtitle?: string;
  generated_at: string;
  kpi_cards: KPICardSpec[];
  primary_chart?: ChartSpec;
  secondary_charts: ChartSpec[];
  filters: FilterSpec[];
  drill_downs?: Array<{ name: string; levels: string[]; current_level: number }>;
  cross_filtering_enabled: boolean;
  insights_panel: boolean;
  insights?: Array<{ rank: number; category: string; title: string; narrative: string; importance: string; confidence: number }>;
  anomalies_summary?: Array<{ column: string; outlier_count: number; outlier_percentage: number; severity: string }>;
}

interface PowerBIDashboardProps {
  spec: DashboardSpec;
  onOpenWhyInvestigation?: (metric: string, dimension?: string) => void;
  onPatchPrompt?: (patchPrompt: string) => void;
  isLoading?: boolean;
}

export const PowerBIDashboard: React.FC<PowerBIDashboardProps> = ({
  spec,
  onOpenWhyInvestigation,
  onPatchPrompt,
  isLoading = false,
}) => {
  // Cross-filtering state: active dimension & value filter
  const [activeCrossFilter, setActiveCrossFilter] = useState<{ dimension: string; value: string } | null>(null);
  const [activeFilters, setActiveFilters] = useState<Record<string, string[]>>({});
  const [patchInput, setPatchInput] = useState('');
  const [chartTypeOverride, setChartTypeOverride] = useState<string | null>(null);

  // Active primary chart type (respecting override if user clicked toggle)
  const activePrimaryType = chartTypeOverride || spec.primary_chart?.type || 'bar';

  // Initialize filters
  const handleFilterToggle = (column: string, value: string) => {
    setActiveFilters(prev => {
      const current = prev[column] || [];
      const updated = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value];
      return { ...prev, [column]: updated };
    });
  };

  const clearAllFilters = () => {
    setActiveFilters({});
    setActiveCrossFilter(null);
  };

  // Cross-filter click handler
  const handleChartElementClick = (entry: any, dimension?: string) => {
    if (!spec.cross_filtering_enabled || !dimension) return;
    const clickedVal = entry?.name || entry?.x || entry?.period;
    if (!clickedVal) return;

    if (activeCrossFilter && activeCrossFilter.dimension === dimension && activeCrossFilter.value === clickedVal) {
      setActiveCrossFilter(null); // toggle off
    } else {
      setActiveCrossFilter({ dimension, value: String(clickedVal) });
    }
  };

  const handlePatchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (patchInput.trim() && onPatchPrompt) {
      onPatchPrompt(patchInput.trim());
      setPatchInput('');
    }
  };

  const exportReportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(spec, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `dashboard_spec_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const defaultColors = ['#0284c7', '#38bdf8', '#818cf8', '#c084fc', '#f472b6', '#34d399', '#fbbf24'];

  return (
    <div className="space-y-6">
      {/* Dashboard Header & Controls Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">{spec.title || 'Power BI Live Executive Dashboard'}</h2>
              <p className="text-xs text-slate-400">{spec.subtitle || 'Self-assembling interactive intelligence view'}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {activeCrossFilter && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-sky-500/20 border border-sky-500/40 text-sky-300 text-xs font-medium animate-pulse">
              <Filter className="w-3.5 h-3.5" />
              <span>Cross-filtered: <strong>{activeCrossFilter.dimension} = {activeCrossFilter.value}</strong></span>
              <button onClick={() => setActiveCrossFilter(null)} className="ml-1 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <button
            onClick={exportReportJSON}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Spec</span>
          </button>
        </div>
      </div>

      {/* Slicers & Global Filter Bar */}
      {spec.filters && spec.filters.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800/80 flex items-center gap-3 overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 shrink-0 font-medium">
            <Filter className="w-3.5 h-3.5 text-sky-400" />
            <span>Slicers:</span>
          </div>

          {spec.filters.map(f => (
            <div key={f.column} className="flex items-center gap-1.5 bg-slate-800/60 border border-slate-700/60 rounded-lg px-2.5 py-1 text-xs shrink-0">
              <span className="text-slate-400 font-medium">{f.title}:</span>
              <div className="flex items-center gap-1">
                {f.options.slice(0, 4).map(opt => {
                  const isSelected = (activeFilters[f.column] || []).includes(opt);
                  return (
                    <button
                      key={opt}
                      onClick={() => handleFilterToggle(f.column, opt)}
                      className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                        isSelected
                          ? 'bg-sky-500 text-white shadow-sm'
                          : 'text-slate-300 hover:bg-slate-700/60'
                      }`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {(Object.keys(activeFilters).length > 0 || activeCrossFilter) && (
            <button
              onClick={clearAllFilters}
              className="text-xs text-rose-400 hover:text-rose-300 ml-auto shrink-0 font-medium underline"
            >
              Reset Filters
            </button>
          )}
        </div>
      )}

      {/* Row 1: KPI Cards with Sparklines & Deltas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {spec.kpi_cards.map(kpi => {
          const sparkData = kpi.sparkline.map((val, idx) => ({ idx, val }));
          return (
            <div
              key={kpi.id}
              className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-lg flex flex-col justify-between relative group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{kpi.title}</span>
                  <div className="text-2xl font-black text-slate-100 mt-1">{kpi.formatted_value}</div>
                  <span className="text-[11px] text-slate-500">{kpi.subtitle || 'Active Measure'}</span>
                </div>

                {/* Delta Badge */}
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-bold ${
                    kpi.is_positive
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}
                >
                  {kpi.is_positive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  <span>{kpi.delta_percentage > 0 ? `+${kpi.delta_percentage}%` : `${kpi.delta_percentage}%`}</span>
                </div>
              </div>

              {/* Sparkline */}
              <div className="h-10 mt-3">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sparkData}>
                    <Line
                      type="monotone"
                      dataKey="val"
                      stroke={kpi.is_positive ? '#34d399' : '#f87171'}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Action: Investigate Why */}
              {onOpenWhyInvestigation && (
                <button
                  onClick={() => onOpenWhyInvestigation(kpi.metric_key)}
                  className="mt-2 text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity font-medium"
                >
                  <span>Investigate drivers (Why?)</span>
                  <ArrowUpRight className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Row 2: Primary Visual Stage & Secondary Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Primary Chart Stage (2 cols) */}
        {spec.primary_chart && (
          <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col justify-between">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-200">{spec.primary_chart.title}</h3>
                <p className="text-xs text-slate-500">Interactive Visual • Click elements to cross-filter report</p>
              </div>

              {/* Chart Type Switcher Toolbar */}
              <div className="flex items-center gap-1 bg-slate-800/80 border border-slate-700/80 rounded-xl p-1 shrink-0">
                {[
                  { key: 'bar', label: 'Bar' },
                  { key: 'horizontal_bar', label: '📉 Bar-H' },
                  { key: 'line', label: 'Line' },
                  { key: 'area', label: '🌊 Area' },
                  { key: 'donut', label: 'Donut' },
                  { key: 'scatter', label: 'Scatter' },
                  { key: 'histogram', label: 'Histogram' },
                ].map(ct => (
                  <button
                    key={ct.key}
                    onClick={() => setChartTypeOverride(ct.key)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all ${
                      activePrimaryType === ct.key
                        ? 'bg-sky-500 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                    }`}
                  >
                    {ct.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Render Primary Chart based on activePrimaryType */}
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                {activePrimaryType === 'area' ? (
                  <AreaChart data={spec.primary_chart.data} onClick={(e: any) => handleChartElementClick(e?.activePayload?.[0]?.payload, spec.primary_chart?.dimension)}>
                    <defs>
                      <linearGradient id="primaryAreaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0284c7" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                    <Area type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2.5} fillOpacity={1} fill="url(#primaryAreaGrad)" />
                  </AreaChart>
                ) : activePrimaryType === 'line' ? (
                  <LineChart data={spec.primary_chart.data} onClick={(e: any) => handleChartElementClick(e?.activePayload?.[0]?.payload, spec.primary_chart?.dimension)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                    <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={3} dot={{ r: 4, fill: '#0284c7' }} />
                  </LineChart>
                ) : activePrimaryType === 'horizontal_bar' ? (
                  <BarChart layout="vertical" data={spec.primary_chart.data} onClick={(e: any) => handleChartElementClick(e?.activePayload?.[0]?.payload, spec.primary_chart?.dimension)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis type="number" stroke="#94a3b8" fontSize={11} />
                    <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={11} width={80} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                    <Bar dataKey="value" fill="#818cf8" radius={[0, 6, 6, 0]}>
                      {spec.primary_chart.data.map((entry, index) => (
                        <Cell
                          key={`cell-hbar-${index}`}
                          fill={activeCrossFilter?.value === entry.name ? '#38bdf8' : (activeCrossFilter ? '#1e293b' : defaultColors[index % defaultColors.length])}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                ) : activePrimaryType === 'donut' || activePrimaryType === 'pie' ? (
                  <PieChart>
                    <Pie
                      data={spec.primary_chart.data}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={95}
                      paddingAngle={3}
                      onClick={(entry: any) => handleChartElementClick(entry, spec.primary_chart?.dimension)}
                    >
                      {spec.primary_chart.data.map((entry, index) => (
                        <Cell
                          key={`cell-donut-${index}`}
                          fill={activeCrossFilter?.value === entry.name ? '#38bdf8' : (activeCrossFilter ? '#1e293b' : defaultColors[index % defaultColors.length])}
                        />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                  </PieChart>
                ) : activePrimaryType === 'scatter' ? (
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis type="number" dataKey="x" name={spec.primary_chart.x_label || 'X'} stroke="#94a3b8" fontSize={11} />
                    <YAxis type="number" dataKey="y" name={spec.primary_chart.y_label || 'Y'} stroke="#94a3b8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                    <Scatter data={spec.primary_chart.data} fill="#38bdf8" />
                  </ScatterChart>
                ) : (
                  <BarChart data={spec.primary_chart.data} onClick={(e: any) => handleChartElementClick(e?.activePayload?.[0]?.payload, spec.primary_chart?.dimension)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                    <Bar dataKey="value" fill="#0284c7" radius={[6, 6, 0, 0]}>
                      {spec.primary_chart.data.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={activeCrossFilter?.value === entry.name ? '#38bdf8' : (activeCrossFilter ? '#1e293b' : defaultColors[index % defaultColors.length])}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>

            {/* Bottom Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 mt-2">
              <span className="text-[11px] text-slate-500 font-mono">
                {spec.primary_chart.data.length} data series points rendered
              </span>
              {onOpenWhyInvestigation && spec.primary_chart.metric && (
                <button
                  onClick={() => onOpenWhyInvestigation(spec.primary_chart!.metric!, spec.primary_chart!.dimension)}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 text-xs font-semibold border border-sky-500/20 transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Investigate Drivers (Why?)</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Secondary Donut / Breakdown Chart (1 col) */}
        {spec.secondary_charts.length > 0 && (
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-200">{spec.secondary_charts[0].title}</h3>
              <p className="text-xs text-slate-500">Distribution proportion</p>
            </div>

            <div className="h-64 w-full my-auto">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={spec.secondary_charts[0].data}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    onClick={(entry: any) => handleChartElementClick(entry, spec.secondary_charts[0].dimension)}
                  >
                    {spec.secondary_charts[0].data.map((entry, index) => (
                      <Cell
                        key={`pie-cell-${index}`}
                        fill={activeCrossFilter?.value === entry.name ? '#38bdf8' : (activeCrossFilter ? '#1e293b' : defaultColors[index % defaultColors.length])}
                      />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Legend pills */}
            <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800">
              {spec.secondary_charts[0].data.map((d, i) => (
                <div key={d.name} className="flex items-center gap-1.5 text-xs text-slate-400">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: defaultColors[i % defaultColors.length] }} />
                  <span>{d.name}: <strong>{d.value}</strong></span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Row 3: Remaining Secondary Visuals */}
      {spec.secondary_charts.length > 1 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {spec.secondary_charts.slice(1).map(sc => (
            <div key={sc.id} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
              <h3 className="text-sm font-bold text-slate-200 mb-1">{sc.title}</h3>
              <p className="text-xs text-slate-500 mb-4">Metric comparison</p>

              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  {sc.type === 'horizontal_bar' ? (
                    <BarChart layout="vertical" data={sc.data} onClick={(e: any) => handleChartElementClick(e?.activePayload?.[0]?.payload, sc.dimension)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                      <XAxis type="number" stroke="#94a3b8" fontSize={11} />
                      <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={11} width={80} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                      <Bar dataKey="value" fill="#818cf8" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  ) : sc.type === 'scatter' ? (
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                      <XAxis type="number" dataKey="x" name={sc.x_label || 'X'} stroke="#94a3b8" fontSize={11} />
                      <YAxis type="number" dataKey="y" name={sc.y_label || 'Y'} stroke="#94a3b8" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                      <Scatter data={sc.data} fill="#34d399" />
                    </ScatterChart>
                  ) : (
                    <BarChart data={sc.data} onClick={(e: any) => handleChartElementClick(e?.activePayload?.[0]?.payload, sc.dimension)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                      <YAxis stroke="#94a3b8" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }} />
                      <Bar dataKey="value" fill="#0284c7" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Row 4: Narrative Insights Panel & Anomaly Callouts */}
      {spec.insights && spec.insights.length > 0 && (
        <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-sky-950/40 border border-sky-500/20 shadow-xl space-y-3">
          <div className="flex items-center gap-2 text-sky-400 text-sm font-bold">
            <Sparkles className="w-4 h-4" />
            <span>AI Narrative Insights & Key Takeaways</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
            {spec.insights.map(item => (
              <div key={item.rank} className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-sky-400">{item.category}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono">
                    {Math.round(item.confidence * 100)}% conf
                  </span>
                </div>
                <h4 className="text-xs font-bold text-slate-200">{item.title}</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">{item.narrative}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Natural Language Dashboard Patch Bar (Incremental Edits) */}
      {onPatchPrompt && (
        <form onSubmit={handlePatchSubmit} className="flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <Sparkles className="w-4 h-4 text-sky-400 shrink-0 ml-2" />
          <input
            type="text"
            value={patchInput}
            onChange={(e) => setPatchInput(e.target.value)}
            placeholder="Edit dashboard: e.g. 'convert primary chart to line', 'filter to North region', 'add slicer for category'..."
            className="flex-1 bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!patchInput.trim() || isLoading}
            className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-medium transition-all"
          >
            Update Report
          </button>
        </form>
      )}
    </div>
  );
};
