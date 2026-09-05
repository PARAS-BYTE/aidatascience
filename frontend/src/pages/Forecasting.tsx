import React, { useState, useEffect } from 'react';
import {
  TrendingUp, Calendar, AlertTriangle, Play, RefreshCw,
  BarChart2, ShieldAlert, Download
} from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Line, Area,
  XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';
import { apiService } from '../services/api';

export const Forecasting: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [dateColumn, setDateColumn] = useState<string>('');
  const [valueColumn, setValueColumn] = useState<string>('');
  const [horizon, setHorizon] = useState<number>(14);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    apiService.getDatasets().then((res) => {
      const items = res.items || [];
      setDatasets(items);
      if (items.length > 0) {
        setSelectedDatasetId(items[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedDatasetId) return;
    apiService.getDatasetPreview(selectedDatasetId, 5).then((data) => {
      if (data && data.columns) {
        setColumns(data.columns);
        // Auto-select date & numeric cols
        const detectedDate = data.columns.find((c: string) =>
          c.toLowerCase().includes('date') || c.toLowerCase().includes('time') || c.toLowerCase().includes('year')
        );
        if (detectedDate) setDateColumn(detectedDate);

        const detectedVal = data.columns.find((c: string) => c !== detectedDate);
        if (detectedVal) setValueColumn(detectedVal);
      }
    }).catch(console.error);
  }, [selectedDatasetId]);

  const handleRunForecast = async () => {
    if (!selectedDatasetId) return;
    setLoading(true);
    try {
      const data = await apiService.forecastTimeSeries(selectedDatasetId, {
        date_column: dateColumn || undefined,
        value_column: valueColumn || undefined,
        horizon: Number(horizon),
      });
      setResult(data);
    } catch (err) {
      console.error('Forecasting error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Combine historical and forecast data for seamless continuous line visualization
  const chartData = React.useMemo(() => {
    if (!result) return [];
    const points: any[] = [];

    (result.historical || []).forEach((h: any) => {
      points.push({
        date: h.date,
        actual: h.actual,
        trend: h.trend,
        is_anomaly: h.is_anomaly,
      });
    });

    // Anchor the forecast to the last actual point
    if (result.forecast && result.forecast.length > 0 && points.length > 0) {
      const lastPoint = points[points.length - 1];
      lastPoint.forecast = lastPoint.actual;
      lastPoint.lower_bound = lastPoint.actual;
      lastPoint.upper_bound = lastPoint.actual;
    }

    (result.forecast || []).forEach((f: any) => {
      points.push({
        date: f.date,
        forecast: f.forecast,
        lower_bound: f.lower_bound,
        upper_bound: f.upper_bound,
      });
    });

    return points;
  }, [result]);

  const exportForecastCSV = () => {
    if (!result || !result.forecast) return;
    const headers = 'Date,Forecast,Lower_Bound_95,Upper_Bound_95\n';
    const rows = result.forecast
      .map((f: any) => `${f.date},${f.forecast},${f.lower_bound},${f.upper_bound}`)
      .join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forecast_${result.dataset_name || 'timeseries'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Time-Series Forecasting</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-medium flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Holt-Winters & Anomaly Detection
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Decompose trend, detect statistical historical anomalies, and project multi-step confidence bands.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl px-3.5 py-2 focus:outline-none focus:border-cyan-500"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename}
              </option>
            ))}
          </select>

          <button
            onClick={handleRunForecast}
            disabled={loading || !selectedDatasetId}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition-all shadow-lg shadow-cyan-600/20 disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>Run Forecast</span>
          </button>
        </div>
      </div>

      {/* Configuration Settings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-900 border border-slate-800 p-4 rounded-2xl">
        <div>
          <label className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-1.5">
            <Calendar className="w-3.5 h-3.5 text-cyan-400" /> Date / Timestamp Column
          </label>
          <select
            value={dateColumn}
            onChange={(e) => setDateColumn(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-cyan-500"
          >
            <option value="">Auto-Detect Timestamp</option>
            {columns.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-1.5">
            <BarChart2 className="w-3.5 h-3.5 text-cyan-400" /> Metric / Value Column
          </label>
          <select
            value={valueColumn}
            onChange={(e) => setValueColumn(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-cyan-500"
          >
            <option value="">Auto-Detect Numeric Metric</option>
            {columns.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-400 flex items-center justify-between mb-1.5">
            <span>Forecast Horizon:</span>
            <span className="text-cyan-400 font-bold">{horizon} steps</span>
          </label>
          <input
            type="range"
            min={3}
            max={60}
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500 mt-2"
          />
        </div>
      </div>

      {/* Metrics Banner */}
      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">Mean Absolute Error (MAE)</p>
            <p className="text-xl font-bold text-slate-100 mt-1">{result.metrics?.mae ?? '—'}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">Root Mean Sq Error (RMSE)</p>
            <p className="text-xl font-bold text-cyan-400 mt-1">{result.metrics?.rmse ?? '—'}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">Mean Absolute % Error (MAPE)</p>
            <p className="text-xl font-bold text-emerald-400 mt-1">{result.metrics?.mape ? `${result.metrics.mape}%` : '—'}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
            <p className="text-xs text-slate-400 font-medium">Historical Anomalies Detected</p>
            <p className="text-xl font-bold text-rose-400 mt-1 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
              {result.anomalies_count ?? 0}
            </p>
          </div>
        </div>
      )}

      {/* Main Forecast Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              Continuous Projection & Confidence Envelope
            </h2>
            <p className="text-xs text-slate-400">
              Blue = Historical actuals; Cyan = Projected values; Shaded = 95% Confidence Interval.
            </p>
          </div>

          {result && (
            <button
              onClick={exportForecastCSV}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors w-fit"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          )}
        </div>

        {chartData.length === 0 ? (
          <div className="h-80 flex flex-col items-center justify-center text-center p-8 border border-dashed border-slate-800 rounded-xl">
            <TrendingUp className="w-10 h-10 text-slate-600 mb-3" />
            <p className="text-sm text-slate-300 font-medium">No forecast calculated yet</p>
            <p className="text-xs text-slate-500 mt-1">Select columns above and click "Run Forecast" to see projections.</p>
          </div>
        ) : (
          <div className="h-96 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} minTickGap={30} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                />
                {/* Confidence Bound Area */}
                <Area
                  type="monotone"
                  dataKey="upper_bound"
                  stroke="none"
                  fill="#06b6d4"
                  fillOpacity={0.15}
                />
                {/* Historical Actual Line */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={{ r: 2, fill: '#38bdf8' }}
                  name="Historical Actual"
                />
                {/* Trend Smoothed Line */}
                <Line
                  type="monotone"
                  dataKey="trend"
                  stroke="#64748b"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  dot={false}
                  name="Decomposed Trend"
                />
                {/* Future Forecast Line */}
                <Line
                  type="monotone"
                  dataKey="forecast"
                  stroke="#06b6d4"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#06b6d4' }}
                  name="Forecast"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Anomalies Table */}
      {result && result.anomalies && result.anomalies.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            Detected Statistical Anomalies ({result.anomalies.length})
          </h3>
          <p className="text-xs text-slate-400">
            Timestamps where actual observed value deviated significantly (&gt; 2.2σ) from the underlying seasonal trend.
          </p>

          <div className="overflow-x-auto rounded-xl border border-slate-800 max-h-56">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-950 text-slate-400 sticky top-0 border-b border-slate-800">
                <tr>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Observed Value</th>
                  <th className="p-3">Expected Trend</th>
                  <th className="p-3">Deviation (Residual)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {result.anomalies.map((a: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="p-3 text-slate-200">{a.date}</td>
                    <td className="p-3 text-rose-300 font-bold">{a.value}</td>
                    <td className="p-3 text-slate-400">{a.expected}</td>
                    <td className="p-3 text-amber-400">{a.deviation > 0 ? `+${a.deviation}` : a.deviation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
