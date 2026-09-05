import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { apiService } from '../services/api';
import { Server, XCircle, ChevronRight, Loader2 } from 'lucide-react';
import { AlertBell } from './AlertBell';

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/datasets': 'Datasets',
  '/eda': 'Exploratory Data Analysis',
  '/ask-data': 'Ask Data (DuckDB)',
  '/cleaning': 'Data Cleaning',
  '/feature-engineering': 'Feature Engineering Studio',
  '/experiments': 'Experiments',
  '/models': 'Model Registry',
  '/forecasting': 'Time-Series Forecasting',
  '/explainability': 'Model Explainability',
  '/multi-agent': 'Multi-Agent Studio',
  '/ai-chat': 'AI Data Scientist',
  '/deployments': 'Deployments',
  '/monitoring': 'Monitoring',
  '/jobs': 'Job Infrastructure',
  '/settings': 'Settings',
};

export const Navbar: React.FC = () => {
  const [health, setHealth] = useState<'ok' | 'error' | 'checking'>('checking');
  const location = useLocation();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await apiService.getHealth();
        if (res.status === 'ok') setHealth('ok');
        else setHealth('error');
      } catch {
        setHealth('error');
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Build breadcrumb
  const pathSegments = location.pathname.split('/').filter(Boolean);
  const currentPage = routeLabels[location.pathname] || routeLabels['/' + pathSegments[0]] || pathSegments[0] || 'Dashboard';

  return (
    <header className="h-14 glass border-b border-slate-800/50 px-8 flex items-center justify-between sticky top-0 z-40">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 animate-fade-in">
        <nav className="flex items-center gap-1.5 text-sm">
          <span className="text-slate-500 font-medium">Platform</span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <span className="text-slate-200 font-semibold">{currentPage}</span>
          {pathSegments.length > 1 && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="text-sky-400 font-mono text-xs">
                {pathSegments[pathSegments.length - 1].slice(0, 8)}...
              </span>
            </>
          )}
        </nav>
      </div>

      <div className="flex items-center gap-3">
        {/* Monitoring & Drift Alerts Bell */}
        <AlertBell />

        {/* Backend Health Badge */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs font-medium transition-all duration-300 ${
          health === 'ok' ? 'border-emerald-500/20' : health === 'error' ? 'border-rose-500/20' : 'border-slate-700'
        }`}>
          <Server className="w-3 h-3 text-slate-400" />
          {health === 'checking' && (
            <span className="flex items-center gap-1.5 text-amber-400">
              <Loader2 className="w-3 h-3 animate-spin" /> Connecting...
            </span>
          )}
          {health === 'ok' && (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
              </span>
              Operational
            </span>
          )}
          {health === 'error' && (
            <span className="flex items-center gap-1.5 text-rose-400">
              <XCircle className="w-3 h-3" /> Offline
            </span>
          )}
        </div>
      </div>
    </header>
  );
};
