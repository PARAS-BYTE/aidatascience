import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Database, BarChart3, Eraser, Sparkles, FlaskConical,
  Box, Brain, MessageSquare, Rocket, Activity, Settings, Cpu,
  ListChecks, ChevronLeft, ChevronRight, Zap, TrendingUp, HelpCircle, User
} from 'lucide-react';

const navSections = [
  {
    label: 'Overview',
    items: [
      { name: 'Dashboard', path: '/', icon: LayoutDashboard },
      { name: 'My Profile', path: '/profile', icon: User },
      { name: 'Datasets', path: '/datasets', icon: Database },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { name: 'EDA', path: '/eda', icon: BarChart3 },
      { name: 'Ask Data', path: '/ask-data', icon: HelpCircle },
      { name: 'Cleaning', path: '/cleaning', icon: Eraser },
      { name: 'Feature Studio', path: '/feature-engineering', icon: Sparkles },
    ],
  },
  {
    label: 'Machine Learning',
    items: [
      { name: 'Experiments', path: '/experiments', icon: FlaskConical },
      { name: 'Models', path: '/models', icon: Box },
      { name: 'Forecasting', path: '/forecasting', icon: TrendingUp },
      { name: 'Explainability', path: '/explainability', icon: Brain },
    ],
  },
  {
    label: 'AI & Ops',
    items: [
      { name: 'Multi-Agent Studio', path: '/multi-agent', icon: Cpu },
      { name: 'AI Data Scientist', path: '/ai-chat', icon: MessageSquare },
      { name: 'Deployments', path: '/deployments', icon: Rocket },
      { name: 'Monitoring', path: '/monitoring', icon: Activity },
    ],
  },
  {
    label: 'System',
    items: [
      { name: 'Jobs', path: '/jobs', icon: ListChecks },
      { name: 'Settings', path: '/settings', icon: Settings },
    ],
  },
];

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`glass-sidebar border-r border-slate-200 flex flex-col shrink-0 h-screen sticky top-0 transition-all duration-300 ease-in-out ${
        collapsed ? 'w-[68px]' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-200 flex items-center gap-3 relative">
        <div className="p-2 rounded-xl bg-blue-600 text-white shadow-sm shrink-0">
          <Zap className="w-5 h-5" />
        </div>
        {!collapsed && (
          <div className="animate-fade-in overflow-hidden">
            <h1 className="text-sm font-bold text-slate-100 tracking-tight whitespace-nowrap">
              AI Data Scientist
            </h1>
            <p className="text-[10px] text-slate-500 font-mono whitespace-nowrap">
              AutoML Platform v1.0
            </p>
          </div>
        )}

        {/* Collapse Toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-all z-20 shadow-sm"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-2 space-y-3 overflow-y-auto overflow-x-hidden">
        {navSections.map((section, sIdx) => (
          <div key={section.label}>
            {!collapsed && (
              <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600 animate-fade-in">
                {section.label}
              </div>
            )}
            {collapsed && sIdx > 0 && (
              <div className="mx-3 my-1 h-px bg-slate-800/60" />
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    title={collapsed ? item.name : undefined}
                    className={({ isActive }) =>
                      `group flex items-center gap-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 relative overflow-hidden ${
                        collapsed ? 'px-2.5 py-2.5 justify-center' : 'px-3 py-2'
                      } ${
                        isActive
                          ? 'bg-blue-50 text-blue-700 shadow-sm'
                          : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {/* Active indicator bar */}
                        {isActive && (
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-blue-600" />
                        )}
                        <Icon className={`w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                          isActive ? 'text-sky-400' : ''
                        }`} />
                        {!collapsed && (
                          <span className="animate-fade-in whitespace-nowrap">{item.name}</span>
                        )}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-slate-200">
        {collapsed ? (
          <div className="flex justify-center">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="System Online" />
          </div>
        ) : (
          <div className="p-2.5 rounded-xl glass-card text-[10px] text-slate-500 animate-fade-in">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50" />
              <span className="font-semibold text-slate-400">System Online</span>
            </div>
            <p className="mt-1 text-slate-600">Deterministic ML + AI Orchestration</p>
          </div>
        )}
      </div>
    </aside>
  );
};
