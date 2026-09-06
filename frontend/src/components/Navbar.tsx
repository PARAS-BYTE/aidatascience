import React, { useEffect, useState, useRef } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Server, XCircle, ChevronRight, Loader2, User as UserIcon, LogOut, Sparkles, ChevronDown } from 'lucide-react';
import { AlertBell } from './AlertBell';
import { AuthModal } from './auth/AuthModal';

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/profile': 'User Profile & Workspace',
  '/datasets': 'Datasets',
  '/eda': 'Exploratory Data Analysis',
  '/ask-data': 'AI Data Scientist (Ask Data)',
  '/cleaning': 'Data Cleaning',
  '/feature-engineering': 'Feature Engineering Studio',
  '/experiments': 'Experiments',
  '/models': 'Model Registry',
  '/forecasting': 'Time-Series Forecasting',
  '/explainability': 'Model Explainability',
  '/multi-agent': 'Multi-Agent Studio',
  '/ai-chat': 'AI Data Scientist (Ask Data & AutoML)',
  '/deployments': 'Deployments',
  '/monitoring': 'Monitoring',
  '/jobs': 'Job Infrastructure',
  '/settings': 'Settings',
};

export const Navbar: React.FC = () => {
  const [health, setHealth] = useState<'ok' | 'error' | 'checking'>('checking');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);

  const { user, openAuthModal, logout, fetchUser } = useAuthStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
    <>
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
          <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs font-medium transition-all duration-300 ${
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

          {/* User Profile / Auth Button */}
          {user ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-2.5 pl-2 pr-3 py-1 rounded-full glass border border-slate-700/60 hover:border-slate-600 transition-all text-xs"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 text-white font-bold flex items-center justify-center text-[11px] shadow-sm">
                  {user.avatar || 'DS'}
                </div>
                <div className="text-left hidden md:block">
                  <span className="font-semibold text-white block leading-tight">{user.name}</span>
                  <span className="text-[10px] text-slate-400 block capitalize">{user.role.replace('_', ' ')}</span>
                </div>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>

              {/* Dropdown Menu */}
              {isUserMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl shadow-2xl p-2 animate-fade-in z-50">
                  <div className="px-3 py-2.5 border-b border-slate-800 mb-1">
                    <p className="text-xs font-semibold text-white truncate">{user.name}</p>
                    <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
                  </div>

                  <Link
                    to="/profile"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-xl transition-colors"
                  >
                    <UserIcon className="w-3.5 h-3.5 text-sky-400" />
                    My Profile & Files
                  </Link>

                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      openAuthModal('login');
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-xl transition-colors text-left"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    Switch User / Login
                  </button>

                  <div className="border-t border-slate-800 mt-1 pt-1">
                    <button
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        logout();
                        navigate('/');
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-rose-400 hover:bg-rose-500/10 rounded-xl transition-colors text-left"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => openAuthModal('login')}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-gradient-to-r from-sky-500 to-indigo-600 text-white font-medium text-xs shadow-md shadow-sky-500/20 hover:from-sky-400 hover:to-indigo-500 transition-all"
            >
              <UserIcon className="w-3.5 h-3.5" />
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Global Auth Modal */}
      <AuthModal />
    </>
  );
};
