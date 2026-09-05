import React, { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Server, Database, FolderCheck, ShieldCheck, Cpu, Sparkles } from 'lucide-react';
import { apiService } from '../services/api';

export const Settings: React.FC = () => {
  const [agentInfo, setAgentInfo] = useState<any>(null);

  useEffect(() => {
    apiService.getAgentModels().then(setAgentInfo).catch(() => {});
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Platform Settings</h1>
        <p className="text-slate-400 text-sm mt-1">
          System configuration, AI models & infrastructure baseline
        </p>
      </div>

      {/* AI & Security Configuration */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h3 className="text-base font-semibold text-slate-100">AI Engine & Prompt Guard Security</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> Groq Prompt Guard Defense
              </div>
              <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full font-medium">
                Active
              </span>
            </div>
            <p className="text-sm font-semibold text-slate-200">
              meta-llama/llama-prompt-guard-2-86m & 22m
            </p>
            <p className="text-xs text-slate-500 font-mono">
              In-flight adversarial prompt injection & jailbreak detection
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
                <Cpu className="w-4 h-4 text-purple-400" /> Groq LLM Orchestration
              </div>
              <span className="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full font-medium">
                Connected
              </span>
            </div>
            <p className="text-sm font-semibold text-slate-200">
              {agentInfo?.active_chat_model || 'openai/gpt-oss-120b'}
            </p>
            <p className="text-xs text-slate-500 font-mono">
              Tool-calling agent grounded in Python ML computation
            </p>
          </div>
        </div>
      </div>

      {/* Environment Overview */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <SettingsIcon className="w-5 h-5 text-sky-400" />
          <h3 className="text-base font-semibold text-slate-100">Environment Overview</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
              <Server className="w-4 h-4 text-sky-400" /> Backend Engine
            </div>
            <p className="text-sm font-semibold text-slate-200">FastAPI (Python 3.11+)</p>
            <p className="text-xs text-slate-500 font-mono">Uvicorn ASGI Server @ :8000</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
              <Database className="w-4 h-4 text-emerald-400" /> Database & ORM
            </div>
            <p className="text-sm font-semibold text-slate-200">PostgreSQL / SQLite Fallback</p>
            <p className="text-xs text-slate-500 font-mono">SQLAlchemy 2.0 + Alembic</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
              <FolderCheck className="w-4 h-4 text-purple-400" /> Local Storage Directories
            </div>
            <p className="text-sm font-semibold text-slate-200">./data/uploads & ./data/results</p>
            <p className="text-xs text-slate-500 font-mono">Path traversal security active</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
              <ShieldCheck className="w-4 h-4 text-amber-400" /> Upload File Limits
            </div>
            <p className="text-sm font-semibold text-slate-200">Max 100 MB / File</p>
            <p className="text-xs text-slate-500 font-mono">Allowed: CSV, XLSX, XLS</p>
          </div>
        </div>
      </div>
    </div>
  );
};
