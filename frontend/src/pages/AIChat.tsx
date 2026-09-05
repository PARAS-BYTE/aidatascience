import React, { useState, useRef, useEffect } from 'react';
import { apiService } from '../services/api';
import {
  MessageSquare, Send, Sparkles, User, Bot, ShieldCheck, ShieldAlert,
  Cpu, BarChart3, PieChart as PieIcon, TrendingUp, Activity,
  Layers, FileSpreadsheet
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line,
  ScatterChart, Scatter, PieChart, Pie, AreaChart, Area,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, ZAxis, Tooltip, CartesianGrid, Cell, Legend
} from 'recharts';

interface GuardInfo {
  is_safe?: boolean;
  score?: number;
  threshold?: number;
  model?: string;
  latency_ms?: number;
  flagged?: boolean;
  reason?: string;
}

interface ChartPayload {
  id?: string;
  type: string;
  title: string;
  description?: string;
  x_key?: string;
  y_key?: string;
  z_key?: string;
  series_keys?: string[];
  data: any[];
  config?: Record<string, any>;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: any[];
  charts?: ChartPayload[];
  guardInfo?: GuardInfo;
  modelUsed?: string;
}

const COLORS = ['#38bdf8', '#a855f7', '#34d399', '#f59e0b', '#f43f5e', '#6366f1', '#ec4899', '#14b8a6', '#eab308'];

const InlineChartRenderer: React.FC<{ chart: ChartPayload }> = ({ chart }) => {
  const { type, title, description, x_key, y_key, z_key, series_keys, data, config } = chart;
  if (!data || data.length === 0) return null;

  // 1. Mini Data Table Preview
  if (type === 'table') {
    const cols = config?.columns || Object.keys(data[0] || {});
    return (
      <div className="my-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            {title}
          </h4>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-mono">
            {config?.total_rows ? `${config.total_rows.toLocaleString()} rows` : `${data.length} rows`}
          </span>
        </div>
        {description && <p className="text-[11px] text-slate-400">{description}</p>}

        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60 max-h-60">
          <table className="w-full text-left font-mono text-[11px]">
            <thead className="bg-slate-950 sticky top-0 border-b border-slate-800 text-slate-400">
              <tr>
                <th className="px-2.5 py-1.5 w-8 text-center text-slate-500 border-r border-slate-800">#</th>
                {cols.map((col: string) => (
                  <th key={col} className="px-3 py-1.5 font-semibold text-slate-300 border-r border-slate-800/60 whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {data.map((row: any, rIdx: number) => (
                <tr key={rIdx} className="hover:bg-slate-800/40">
                  <td className="px-2.5 py-1 text-center text-[10px] text-slate-500 border-r border-slate-800 select-none">
                    {rIdx + 1}
                  </td>
                  {cols.map((col: string) => {
                    const val = row[col];
                    const isNull = val === null || val === undefined;
                    return (
                      <td key={col} className={`px-3 py-1 border-r border-slate-800/40 truncate max-w-xs ${isNull ? 'text-slate-600 italic' : 'text-slate-300'}`}>
                        {isNull ? 'null' : String(val)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // 2. Box Plot / Statistical Distribution Summary Card
  if (type === 'boxplot') {
    return (
      <div className="my-3 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-purple-400" />
            {title}
          </h4>
          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/40 font-mono uppercase">
            Box Plot
          </span>
        </div>
        {description && <p className="text-[11px] text-slate-400">{description}</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          {data.map((box: any, bIdx: number) => {
            const range = Math.max(0.01, (box.max || 1) - (box.min || 0));
            const q1Pct = Math.max(0, Math.min(100, (((box.q1 - box.min) / range) * 100)));
            const medPct = Math.max(0, Math.min(100, (((box.median - box.min) / range) * 100)));
            const q3Pct = Math.max(0, Math.min(100, (((box.q3 - box.min) / range) * 100)));

            return (
              <div key={bIdx} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">{box.category}</span>
                  <span className="text-[11px] text-slate-400 font-mono">Mean: {box.mean}</span>
                </div>

                {/* Visual Box-Whisker Bar */}
                <div className="relative h-6 bg-slate-950 rounded-md border border-slate-800 flex items-center px-1 overflow-hidden my-1.5">
                  {/* Whisker Line */}
                  <div className="absolute left-2 right-2 h-0.5 bg-slate-600" />
                  {/* IQR Box */}
                  <div
                    className="absolute h-4 bg-purple-500/30 border border-purple-400/80 rounded-sm"
                    style={{ left: `${q1Pct}%`, width: `${Math.max(4, q3Pct - q1Pct)}%` }}
                  />
                  {/* Median Line */}
                  <div
                    className="absolute h-5 w-1 bg-amber-400 z-10 rounded-full"
                    style={{ left: `${medPct}%` }}
                    title={`Median: ${box.median}`}
                  />
                </div>

                {/* Five-Number Summary Pills */}
                <div className="grid grid-cols-5 gap-1 text-[10px] text-center font-mono pt-1">
                  <div className="bg-slate-950/80 p-1 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">MIN</span>
                    <span className="text-slate-300">{box.min}</span>
                  </div>
                  <div className="bg-slate-950/80 p-1 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">Q1</span>
                    <span className="text-purple-300">{box.q1}</span>
                  </div>
                  <div className="bg-purple-950/40 p-1 rounded border border-purple-800/40 font-bold">
                    <span className="text-amber-400 block text-[9px]">MED</span>
                    <span className="text-amber-300">{box.median}</span>
                  </div>
                  <div className="bg-slate-950/80 p-1 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">Q3</span>
                    <span className="text-purple-300">{box.q3}</span>
                  </div>
                  <div className="bg-slate-950/80 p-1 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">MAX</span>
                    <span className="text-slate-300">{box.max}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // 3. Radar Chart
  if (type === 'radar') {
    return (
      <div className="my-3 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-purple-400" />
            {title}
          </h4>
          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/40 uppercase font-mono">
            Radar
          </span>
        </div>
        {description && <p className="text-[11px] text-slate-400">{description}</p>}

        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey={x_key || 'subject'} stroke="#94a3b8" tick={{ fontSize: 10, fill: '#cbd5e1' }} />
              <PolarRadiusAxis stroke="#475569" angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              <Radar name={title} dataKey={y_key || 'value'} stroke="#a855f7" fill="#a855f7" fillOpacity={0.45} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  }

  // 4. Standard & Universal Recharts (Area, Donut, Line, Scatter, Bubble, Bar, Horizontal Bar, Stacked)
  return (
    <div className="my-3 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
          {type === 'pie' || type === 'donut' ? (
            <PieIcon className="w-3.5 h-3.5 text-purple-400" />
          ) : type === 'line' || type === 'multi_line' ? (
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <BarChart3 className="w-3.5 h-3.5 text-sky-400" />
          )}
          {title}
        </h4>
        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 uppercase font-mono">
          {type}
        </span>
      </div>
      {description && <p className="text-[11px] text-slate-400">{description}</p>}

      <div className="h-64 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          {type === 'area' || type === 'stacked_area' ? (
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`grad_${title.replace(/\s+/g, '_')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey={x_key || Object.keys(data[0])[0]} stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              <Area
                type="monotone"
                dataKey={y_key || Object.keys(data[0])[1]}
                stroke="#38bdf8"
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#grad_${title.replace(/\s+/g, '_')})`}
              />
            </AreaChart>
          ) : type === 'line' || type === 'multi_line' ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey={x_key || Object.keys(data[0])[0]} stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              {series_keys && series_keys.length > 0 ? (
                <>
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                  {series_keys.map((sKey, sIdx) => (
                    <Line
                      key={sKey}
                      type="monotone"
                      dataKey={sKey}
                      stroke={COLORS[sIdx % COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 2 }}
                    />
                  ))}
                </>
              ) : (
                <Line type="monotone" dataKey={y_key || Object.keys(data[0])[1]} stroke="#38bdf8" strokeWidth={2} dot={{ fill: '#38bdf8' }} />
              )}
            </LineChart>
          ) : type === 'scatter' || type === 'bubble' ? (
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey={x_key || Object.keys(data[0])[0]} name={x_key || 'X'} stroke="#64748b" fontSize={10} />
              <YAxis dataKey={y_key || Object.keys(data[0])[1]} name={y_key || 'Y'} stroke="#64748b" fontSize={10} />
              {type === 'bubble' && <ZAxis dataKey={z_key || 'size'} range={[40, 400]} name={z_key || 'Size'} />}
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              <Scatter name={title} data={data} fill="#a855f7" />
            </ScatterChart>
          ) : type === 'pie' || type === 'donut' ? (
            <PieChart>
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              <Pie
                data={data}
                dataKey={y_key || 'count'}
                nameKey={x_key || 'category'}
                cx="50%"
                cy="50%"
                innerRadius={type === 'donut' ? 45 : 0}
                outerRadius={80}
                label={({ name, percent }: any) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
            </PieChart>
          ) : type === 'horizontal_bar' ? (
            <BarChart layout="vertical" data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" stroke="#64748b" fontSize={10} />
              <YAxis dataKey={y_key || 'category'} type="category" stroke="#64748b" fontSize={10} width={80} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              <Bar dataKey={x_key || 'value'} fill="#38bdf8" radius={[0, 4, 4, 0]}>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          ) : type === 'stacked_bar' && series_keys ? (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey={x_key || 'category'} stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
              {series_keys.map((sKey, sIdx) => (
                <Bar key={sKey} dataKey={sKey} stackId="a" fill={COLORS[sIdx % COLORS.length]} radius={[2, 2, 0, 0]} />
              ))}
            </BarChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey={x_key || Object.keys(data[0])[0]} stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              {series_keys && series_keys.length > 0 ? (
                <>
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                  {series_keys.map((sKey, sIdx) => (
                    <Bar key={sKey} dataKey={sKey} fill={COLORS[sIdx % COLORS.length]} radius={[3, 3, 0, 0]} />
                  ))}
                </>
              ) : (
                <Bar dataKey={y_key || Object.keys(data[0])[1]} fill="#38bdf8" radius={[4, 4, 0, 0]}>
                  {data.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              )}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export const AIChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [guardModel, setGuardModel] = useState('meta-llama/llama-prompt-guard-2-86m');
  const [llmModel, setLlmModel] = useState('openai/gpt-oss-120b');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiService.getDatasets().then(r => {
      setDatasets(r.items || []);
      if (r.items?.length > 0) setSelectedDataset(r.items[0].id);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (textToSend?: string) => {
    const userMsg = (textToSend || input).trim();
    if (!userMsg || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const result = await apiService.agentChat(
        userMsg,
        sessionId || undefined,
        selectedDataset || undefined,
        guardModel,
        llmModel,
      );
      setSessionId(result.session_id);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: result.response,
        toolCalls: result.tool_calls,
        charts: result.charts,
        guardInfo: result.guard_info,
        modelUsed: result.model_used,
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error communicating with the AI Engine. Please verify the backend is running.',
      }]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renderMarkdown = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inTable = false;
    let tableLines: string[] = [];

    lines.forEach((line, i) => {
      if (line.startsWith('|')) {
        if (!inTable) {
          inTable = true;
          tableLines = [];
        }
        tableLines.push(line);
        return;
      } else if (inTable) {
        inTable = false;
        const rows = tableLines.filter(l => !l.match(/^\|[-\s|]+\|$/));
        if (rows.length > 0) {
          const headers = rows[0].split('|').filter(Boolean).map(s => s.trim());
          const body = rows.slice(1).map(r => r.split('|').filter(Boolean).map(s => s.trim()));
          elements.push(
            <div key={`table-${i}`} className="overflow-x-auto my-2 rounded-lg border border-slate-700/60 bg-slate-900/50">
              <table className="w-full text-xs text-left">
                <thead className="text-slate-400 bg-slate-800/80 border-b border-slate-700">
                  <tr>{headers.map((h, hi) => <th key={hi} className="px-3 py-2 font-semibold">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {body.map((row, ri) => (
                    <tr key={ri} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                      {row.map((cell, ci) => <td key={ci} className="px-3 py-1.5 text-slate-300 font-mono">{cell}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        tableLines = [];
      }

      if (line.startsWith('## ')) {
        elements.push(<h3 key={i} className="text-sm font-bold text-slate-100 mt-3 mb-1">{line.replace('## ', '')}</h3>);
      } else if (line.startsWith('### ')) {
        elements.push(<h4 key={i} className="text-xs font-semibold text-slate-200 mt-2 mb-1">{line.replace('### ', '')}</h4>);
      } else if (line.startsWith('• ') || line.startsWith('- ')) {
        const content = line.replace(/^[•\-]\s*/, '');
        elements.push(
          <p key={i} className="text-sm text-slate-300 pl-3 py-0.5" dangerouslySetInnerHTML={{
            __html: '• ' + content.replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-100 font-semibold">$1</strong>')
              .replace(/`(.*?)`/g, '<code class="bg-slate-950/80 px-1.5 py-0.5 rounded text-sky-400 font-mono text-xs border border-slate-800">$1</code>')
          }} />
        );
      } else if (line.trim()) {
        elements.push(
          <p key={i} className="text-sm text-slate-300 py-0.5" dangerouslySetInnerHTML={{
            __html: line.replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-100 font-semibold">$1</strong>')
              .replace(/`(.*?)`/g, '<code class="bg-slate-950/80 px-1.5 py-0.5 rounded text-sky-400 font-mono text-xs border border-slate-800">$1</code>')
          }} />
        );
      }
    });

    return elements;
  };

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-800 p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-purple-500 via-indigo-500 to-pink-500 text-white shadow-lg shadow-purple-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-100">AI Data Scientist</h1>
              <span className="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full font-medium flex items-center gap-1">
                <Cpu className="w-3 h-3" /> Groq Engine
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous data analytics & dynamic chart generation</p>
          </div>
        </div>

        {/* Model & Dataset Pickers */}
        <div className="flex items-center gap-2">
          {/* Prompt Guard Model Switcher */}
          <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-lg px-2.5 py-1 text-xs">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400 text-[11px]">Guard:</span>
            <select
              value={guardModel}
              onChange={e => setGuardModel(e.target.value)}
              className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
            >
              <option value="meta-llama/llama-prompt-guard-2-86m" className="bg-slate-900">
                Prompt Guard 2 (86M)
              </option>
              <option value="meta-llama/llama-prompt-guard-2-22m" className="bg-slate-900">
                Prompt Guard 2 (22M)
              </option>
            </select>
          </div>

          {/* Groq LLM Model Switcher */}
          <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-lg px-2.5 py-1 text-xs">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-slate-400 text-[11px]">LLM:</span>
            <select
              value={llmModel}
              onChange={e => setLlmModel(e.target.value)}
              className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
            >
              <option value="openai/gpt-oss-120b" className="bg-slate-900">GPT-OSS 120B</option>
              <option value="openai/gpt-oss-20b" className="bg-slate-900">GPT-OSS 20B</option>
              <option value="qwen/qwen3.8-27b" className="bg-slate-900">Qwen 3.8 27B</option>
              <option value="groq/compound" className="bg-slate-900">Groq Compound</option>
            </select>
          </div>

          {/* Dataset Switcher */}
          <select
            value={selectedDataset}
            onChange={e => { setSelectedDataset(e.target.value); setSessionId(null); setMessages([]); }}
            className="bg-slate-800/80 border border-slate-700/80 text-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-sky-500"
          >
            <option value="">No dataset selected</option>
            {datasets.map(d => <option key={d.id} value={d.id}>{d.original_filename}</option>)}
          </select>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-10 space-y-4 max-w-xl mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-500/20 to-pink-500/20 border border-purple-500/30 flex items-center justify-center mx-auto text-purple-400">
              <MessageSquare className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-200">Ask the AI Data Scientist</h3>
              <p className="text-xs text-slate-400 mt-1">
                Ask questions, generate interactive charts, and run end-to-end AutoML.
              </p>
            </div>

            <div className="flex flex-wrap justify-center gap-2 pt-2">
              <button
                onClick={() => sendMessage('Run AI Auto-Pilot pipeline on this dataset')}
                className="text-xs px-4 py-2 bg-gradient-to-r from-purple-600/30 to-indigo-600/30 text-purple-300 border border-purple-500/40 rounded-xl hover:border-purple-400 hover:text-white transition-all shadow-md font-semibold flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
                Run full AI Auto-Pilot pipeline
              </button>
              {[
                'Show CSV head preview',
                'Box plot of numerical features',
                'Donut chart category breakdown',
                'Radar chart of feature profile',
                'Area distribution curve',
                'Stacked category bar chart',
                'Scatter plot of first two numeric columns',
                'Compare models in a chart',
                'Profile this dataset',
                'Show SHAP feature importance',
              ].map(q => (
                <button
                  key={q}
                  onClick={() => sendMessage(q.replace(/^[^\w\s]+\s*/, ''))}
                  className="text-xs px-3.5 py-2 bg-slate-900/90 text-slate-300 border border-slate-800 rounded-xl hover:border-purple-500/50 hover:text-white transition-all shadow-sm"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="shrink-0 w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center shadow">
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-lg ${
              msg.role === 'user'
                ? 'bg-gradient-to-r from-sky-600 to-sky-500 text-white shadow-sky-500/10'
                : 'bg-slate-900 border border-slate-800/90 text-slate-200'
            }`}>
              {msg.role === 'user' ? (
                <p className="text-sm">{msg.content}</p>
              ) : (
                <div>
                  <div>{renderMarkdown(msg.content)}</div>

                  {/* Render Visual Charts if returned */}
                  {msg.charts && msg.charts.length > 0 && (
                    <div className="space-y-3 my-2">
                      {msg.charts.map((chart, cIdx) => (
                        <InlineChartRenderer key={chart.id || cIdx} chart={chart} />
                      ))}
                    </div>
                  )}

                  {/* Prompt Guard & Tool Call Badges */}
                  <div className="mt-3 pt-2.5 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {Boolean(msg.toolCalls && msg.toolCalls.length > 0) && (
                        msg.toolCalls!.map((tc: any, ti: number) => (
                          <span key={ti} className="px-2 py-0.5 bg-purple-950/60 border border-purple-800/40 text-purple-300 rounded-md font-mono text-[10px]">
                            Tool: {tc.tool}
                          </span>
                        ))
                      )}
                    </div>

                    {msg.guardInfo && (
                      <div className="flex items-center gap-1">
                        {msg.guardInfo.flagged ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-950/60 border border-red-800/50 text-red-400 rounded-md text-[10px]">
                            <ShieldAlert className="w-3 h-3" /> Blocked ({msg.guardInfo.score?.toFixed(4)})
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 rounded-md text-[10px]" title={`Prompt Guard score: ${msg.guardInfo.score} | Latency: ${msg.guardInfo.latency_ms}ms`}>
                            <ShieldCheck className="w-3 h-3" /> Guard: {msg.guardInfo.score?.toFixed(4)} ({msg.guardInfo.model?.includes('22m') ? '22M' : '86M'})
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="shrink-0 w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/30 flex items-center justify-center">
                <User className="w-4 h-4 text-sky-400" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="shrink-0 w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-2xl px-4 py-3 flex items-center gap-2">
              <span className="text-xs text-slate-400">Executing agent tools & generating visual analysis...</span>
              <div className="flex gap-1 ml-1">
                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-slate-800 p-4 bg-slate-900/60 backdrop-blur">
        <div className="flex items-center gap-3 max-w-5xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask for graphs, analysis, model comparisons, or data profiling..."
            className="flex-1 bg-slate-800/90 border border-slate-700/80 text-slate-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 placeholder-slate-500 transition-colors"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="p-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl disabled:opacity-50 transition-all shadow-lg shadow-purple-500/20"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
