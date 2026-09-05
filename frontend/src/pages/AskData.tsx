import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare, Send, Sparkles, Database, Terminal,
  BarChart3, RefreshCw, ChevronDown, ChevronRight, AlertCircle
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';
import { apiService } from '../services/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  data?: {
    sql: string;
    columns: string[];
    rows: any[];
    row_count: number;
    explanation: string;
    recommended_chart?: string;
    chart_type?: string;
    x_axis?: string;
    y_axis?: string;
  };
  error?: string;
}

const COLORS = ['#38bdf8', '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#a78bfa', '#f87171'];

export const AskData: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [expandedSql, setExpandedSql] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const q = textToSend || query;
    if (!q.trim() || !selectedDatasetId || loading) return;

    const userMsgId = `user_${Date.now()}`;
    const newMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newMsg]);
    if (!textToSend) setQuery('');
    setLoading(true);

    try {
      const res = await apiService.askData(selectedDatasetId, q);
      const assistantMsg: ChatMessage = {
        id: `ast_${Date.now()}`,
        sender: 'assistant',
        text: res.explanation || 'Here are the results query from your dataset:',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        data: res,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: 'assistant',
        text: 'Sorry, I encountered an error translating or executing that query.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        error: err.response?.data?.detail || err.message || 'Execution error',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const samplePrompts = [
    'Show the top 10 rows',
    'What is the count of rows and columns?',
    'Show average of numeric columns',
    'Count missing or null values across features',
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] space-y-4 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-2xl">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                Ask Data <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">DuckDB Text-to-SQL</span>
              </h1>
              <p className="text-xs text-slate-400">
                Ask questions in plain English. Powered by zero-copy DuckDB execution engine.
              </p>
            </div>
          </div>
        </div>

        {/* Dataset Dropdown */}
        <div className="flex items-center gap-3">
          <Database className="w-4 h-4 text-slate-400" />
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-3.5 py-2 focus:outline-none focus:border-sky-500"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename} ({d.row_count?.toLocaleString() || 0} rows)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Chat Scroll Area */}
      <div className="flex-1 overflow-y-auto bg-slate-950/60 border border-slate-800/80 rounded-2xl p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4 py-16">
            <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 shadow-xl shadow-sky-500/10">
              <Sparkles className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-200">What would you like to know?</h3>
              <p className="text-xs text-slate-400 mt-1">
                Ask about the selected dataset in plain language. Your question is translated into a safe, read-only query and the result is shown below.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full pt-2">
              {samplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(p)}
                  className="text-left text-xs px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-sky-300 hover:border-sky-500/40 hover:bg-slate-800/50 transition-all flex items-center justify-between"
                >
                  <span>{p}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              {/* Message Header */}
              <div className="flex items-center gap-2 mb-1 px-1">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  {msg.sender === 'user' ? 'You' : 'DuckDB Agent'}
                </span>
                <span className="text-[10px] text-slate-600">{msg.timestamp}</span>
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-3xl rounded-2xl p-4 text-sm ${
                  msg.sender === 'user'
                    ? 'bg-sky-600 text-white rounded-tr-sm shadow-lg shadow-sky-600/20'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-sm space-y-4 shadow-lg'
                }`}
              >
                <p className="leading-relaxed">{msg.text}</p>

                {/* Error Banner */}
                {msg.error && (
                  <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                    <span>{msg.error}</span>
                  </div>
                )}

                {/* Data Payload */}
                {msg.data && (
                  <div className="space-y-4 pt-1">
                    {/* Collapsible SQL View */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
                      <button
                        onClick={() =>
                          setExpandedSql((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))
                        }
                        className="w-full flex items-center justify-between px-3 py-2 text-xs font-mono text-slate-400 hover:bg-slate-900/60 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Terminal className="w-3.5 h-3.5 text-sky-400" />
                          <span>Generated SQL Query</span>
                        </div>
                        {expandedSql[msg.id] ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {expandedSql[msg.id] && (
                        <div className="p-3 bg-slate-950 border-t border-slate-800/80 font-mono text-[11px] text-sky-300 overflow-x-auto whitespace-pre">
                          {msg.data.sql}
                        </div>
                      )}
                    </div>

                    {/* Chart Visualization if Applicable */}
                    {msg.data.rows && msg.data.rows.length > 0 && (msg.data.recommended_chart || msg.data.chart_type) !== 'table' && (
                      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/80 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                          <span className="flex items-center gap-1.5 text-sky-400">
                            <BarChart3 className="w-3.5 h-3.5" /> Visualization ({msg.data.recommended_chart || msg.data.chart_type})
                          </span>
                          <span>{msg.data.row_count} rows</span>
                        </div>
                        <div className="h-60 w-full pt-2">
                          <ResponsiveContainer width="100%" height="100%">
                            {(msg.data.recommended_chart || msg.data.chart_type) === 'line' ? (
                              <LineChart data={msg.data.rows}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey={msg.data.x_axis || msg.data.columns[0]} stroke="#64748b" fontSize={10} />
                                <YAxis stroke="#64748b" fontSize={10} />
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                                <Line type="monotone" dataKey={msg.data.y_axis || msg.data.columns[1]} stroke="#38bdf8" strokeWidth={2} dot={false} />
                              </LineChart>
                            ) : (msg.data.recommended_chart || msg.data.chart_type) === 'pie' ? (
                              <PieChart>
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                                <Pie
                                  data={msg.data.rows}
                                  dataKey={msg.data.y_axis || msg.data.columns[1]}
                                  nameKey={msg.data.x_axis || msg.data.columns[0]}
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={70}
                                >
                                  {msg.data.rows.map((_, i) => (
                                    <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                                  ))}
                                </Pie>
                              </PieChart>
                            ) : (
                              <BarChart data={msg.data.rows}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey={msg.data.x_axis || msg.data.columns[0]} stroke="#64748b" fontSize={10} />
                                <YAxis stroke="#64748b" fontSize={10} />
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                                <Bar dataKey={msg.data.y_axis || msg.data.columns[1]} fill="#38bdf8" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            )}
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )}

                    {/* Table Preview */}
                    {msg.data.rows && msg.data.rows.length > 0 && (
                      <div className="rounded-xl border border-slate-800 overflow-hidden">
                        <div className="max-h-48 overflow-auto">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead className="bg-slate-950 text-slate-400 sticky top-0 border-b border-slate-800">
                              <tr>
                                {msg.data.columns.map((c) => (
                                  <th key={c} className="p-2.5 font-mono whitespace-nowrap">{c}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                              {msg.data.rows.slice(0, 15).map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-slate-800/30">
                                  {msg.data?.columns.map((c) => (
                                    <td key={c} className="p-2.5 whitespace-nowrap text-slate-300">
                                      {row[c] !== null && row[c] !== undefined ? String(row[c]) : <span className="text-slate-600">null</span>}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-center gap-2 p-3 bg-slate-900 border border-slate-800 rounded-2xl w-fit text-xs text-slate-400 animate-pulse">
            <RefreshCw className="w-4 h-4 animate-spin text-sky-400" />
            <span>Formulating SQL and running in DuckDB...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-3 bg-slate-900 border border-slate-800 p-2.5 rounded-2xl"
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about this dataset (e.g. Which category has the highest sales?)..."
          disabled={loading || !selectedDatasetId}
          className="flex-1 bg-transparent border-0 text-sm text-slate-200 placeholder-slate-500 focus:outline-none px-3"
        />
        <button
          type="submit"
          disabled={loading || !query.trim() || !selectedDatasetId}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-xs transition-all shadow-lg shadow-sky-500/20 disabled:opacity-40"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          <span>Send</span>
        </button>
      </form>
    </div>
  );
};
