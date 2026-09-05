import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { Link } from 'react-router-dom';
import {
  User,
  Database,
  Brain,
  Award,
  Activity,
  FileSpreadsheet,
  Clock,
  ArrowUpRight,
  CheckCircle2,
  HardDrive,
  Edit3,
  Search,
  RefreshCw,
  LogOut,
} from 'lucide-react';

export const Profile: React.FC = () => {
  const {
    user,
    profileSummary,
    fetchProfileSummary,
    isSummaryLoading,
    openAuthModal,
    logout,
    updateProfile,
  } = useAuthStore();

  const [activeTab, setActiveTab] = useState<'datasets' | 'models' | 'timeline' | 'edit'>('datasets');
  const [searchTerm, setSearchTerm] = useState('');
  const [editName, setEditName] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editSaved, setEditSaved] = useState(false);

  useEffect(() => {
    fetchProfileSummary();
  }, [fetchProfileSummary]);

  useEffect(() => {
    if (user) {
      setEditName(user.name);
      setEditBio(user.bio || '');
    }
  }, [user]);

  if (!user) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center py-20 animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center mx-auto mb-4">
          <User className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Sign in to View Your Profile</h2>
        <p className="text-slate-400 text-sm max-w-md mx-auto mb-6">
          Each data scientist has their own isolated workspace, uploaded datasets, trained models, and activity timeline.
        </p>
        <button
          onClick={() => openAuthModal('login')}
          className="px-6 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 text-white font-medium text-sm rounded-xl shadow-lg shadow-sky-500/25 hover:from-sky-400 hover:to-indigo-500 transition-all"
        >
          Sign In or Register
        </button>
      </div>
    );
  }

  const stats = profileSummary?.stats || {
    datasets_count: 0,
    total_storage_bytes: 0,
    models_count: 0,
    experiments_count: 0,
    jobs_count: 0,
    best_accuracy: undefined,
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 KB';
    const k = 1024;
    const dm = 1;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await updateProfile({ name: editName, bio: editBio });
    if (success) {
      setEditSaved(true);
      setTimeout(() => setEditSaved(false), 3000);
    }
  };

  const filteredDatasets = (profileSummary?.uploaded_datasets || []).filter((d) =>
    d.original_filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto animate-fade-in">
      {/* ─── Profile Header Card ────────────────────────────────────────── */}
      <div className="relative glass border border-slate-700/60 rounded-3xl p-6 md:p-8 overflow-hidden shadow-xl">
        <div className="absolute -top-16 -right-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 text-white flex items-center justify-center text-2xl font-bold shadow-lg shadow-sky-500/30 ring-4 ring-slate-800">
              {user.avatar || 'DS'}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">{user.name}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30 uppercase tracking-wider">
                  {user.role.replace('_', ' ')}
                </span>
              </div>
              <p className="text-slate-400 text-sm mt-1">{user.email}</p>
              {user.bio && <p className="text-slate-300 text-xs mt-2 italic max-w-xl">{user.bio}</p>}
            </div>
          </div>

          <div className="flex items-center gap-3 self-end md:self-center">
            <button
              onClick={() => fetchProfileSummary()}
              disabled={isSummaryLoading}
              className="p-2.5 rounded-xl glass hover:bg-slate-800 text-slate-400 hover:text-white transition-colors border border-slate-700/60"
              title="Refresh profile stats"
            >
              <RefreshCw className={`w-4 h-4 ${isSummaryLoading ? 'animate-spin text-sky-400' : ''}`} />
            </button>
            <button
              onClick={() => setActiveTab('edit')}
              className="flex items-center gap-2 px-4 py-2 rounded-xl glass hover:bg-slate-800 text-slate-200 text-xs font-semibold transition-all border border-slate-700/60"
            >
              <Edit3 className="w-3.5 h-3.5 text-sky-400" />
              Edit Profile
            </button>
            <button
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold transition-all border border-rose-500/20"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign Out
            </button>
          </div>
        </div>

        {/* ─── Metric KPI Stats Grid ────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 mt-8 pt-6 border-t border-slate-800/80">
          <div className="p-3.5 rounded-2xl bg-slate-800/40 border border-slate-700/40">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-medium">Uploaded Datasets</span>
              <Database className="w-4 h-4 text-sky-400" />
            </div>
            <div className="text-xl font-bold text-white">{stats.datasets_count}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">CSV & Excel files</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-800/40 border border-slate-700/40">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-medium">Storage Used</span>
              <HardDrive className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-xl font-bold text-white">{formatBytes(stats.total_storage_bytes)}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Disk footprint</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-800/40 border border-slate-700/40">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-medium">Models Trained</span>
              <Brain className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-xl font-bold text-white">{stats.models_count}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">ML artifacts</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-800/40 border border-slate-700/40">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-medium">Best Accuracy</span>
              <Award className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-xl font-bold text-emerald-400">
              {stats.best_accuracy !== null && stats.best_accuracy !== undefined
                ? stats.best_accuracy <= 1.0
                  ? `${(stats.best_accuracy * 100).toFixed(1)}%`
                  : stats.best_accuracy.toFixed(3)
                : 'N/A'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Top score</div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-800/40 border border-slate-700/40">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-medium">Jobs Completed</span>
              <Activity className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-xl font-bold text-white">{stats.jobs_count}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Pipelines run</div>
          </div>
        </div>
      </div>

      {/* ─── Navigation Tabs ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('datasets')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'datasets'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/25'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            My Uploaded Datasets ({stats.datasets_count})
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'models'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/25'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            My Trained Models ({stats.models_count})
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'timeline'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/25'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Activity Timeline
          </button>
          <button
            onClick={() => setActiveTab('edit')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'edit'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/25'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" />
            Edit Profile
          </button>
        </div>

        {activeTab === 'datasets' && (
          <div className="relative hidden sm:block">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter datasets..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-800/60 border border-slate-700/60 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 w-48"
            />
          </div>
        )}
      </div>

      {/* ─── Tab Content: Datasets ───────────────────────────────────────── */}
      {activeTab === 'datasets' && (
        <div className="glass border border-slate-700/60 rounded-2xl overflow-hidden shadow-lg">
          {filteredDatasets.length === 0 ? (
            <div className="p-12 text-center">
              <FileSpreadsheet className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h4 className="text-white font-medium text-base mb-1">No datasets found</h4>
              <p className="text-slate-400 text-xs max-w-sm mx-auto mb-4">
                You haven't uploaded any CSV or Excel files yet. Upload a dataset to begin exploratory analysis and model training.
              </p>
              <Link
                to="/datasets"
                className="inline-flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-400 text-white rounded-xl text-xs font-semibold transition-all shadow-md shadow-sky-500/20"
              >
                Upload First Dataset
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-700/60">
                  <tr>
                    <th className="py-3 px-5">Dataset File</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Size</th>
                    <th className="py-3 px-4">Rows × Cols</th>
                    <th className="py-3 px-4">Uploaded Date</th>
                    <th className="py-3 px-4 text-right">Quick Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {filteredDatasets.map((d) => (
                    <tr key={d.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-5 font-medium text-white flex items-center gap-2.5">
                        <FileSpreadsheet className="w-4 h-4 text-sky-400 flex-shrink-0" />
                        <span className="truncate max-w-xs">{d.original_filename}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded-md bg-slate-800 text-sky-400 font-mono text-[11px] border border-slate-700">
                          {d.file_type}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">{formatBytes(d.file_size)}</td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {d.rows ? `${d.rows.toLocaleString()} × ${d.columns}` : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {new Date(d.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-2">
                        <Link
                          to={`/eda`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 text-[11px] font-semibold transition-colors"
                        >
                          Explore (EDA)
                        </Link>
                        <Link
                          to={`/cleaning`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[11px] font-semibold transition-colors"
                        >
                          Clean
                        </Link>
                        <Link
                          to={`/experiments`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 text-[11px] font-semibold transition-colors"
                        >
                          Train
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ─── Tab Content: Models ─────────────────────────────────────────── */}
      {activeTab === 'models' && (
        <div className="space-y-4">
          {(profileSummary?.trained_models || []).length === 0 ? (
            <div className="glass border border-slate-700/60 rounded-2xl p-12 text-center">
              <Brain className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h4 className="text-white font-medium text-base mb-1">No trained models yet</h4>
              <p className="text-slate-400 text-xs max-w-sm mx-auto mb-4">
                Run an AutoML training pipeline on any of your uploaded datasets to train scikit-learn and XGBoost models.
              </p>
              <Link
                to="/experiments"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-sky-500 to-indigo-600 text-white rounded-xl text-xs font-semibold shadow-md shadow-sky-500/20"
              >
                Go to Experiments Studio
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {profileSummary?.trained_models.map((m) => (
                <div
                  key={m.id}
                  className="glass border border-slate-700/60 rounded-2xl p-5 hover:border-slate-600 transition-all shadow-md group"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <h4 className="text-white font-semibold text-sm group-hover:text-sky-400 transition-colors">
                        {m.name}
                      </h4>
                      <p className="text-slate-400 text-[11px] mt-0.5 capitalize">
                        Target: <span className="text-slate-200 font-mono">{m.target_column}</span>
                      </p>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 uppercase">
                      {m.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-2 border-y border-slate-800 text-xs mb-3">
                    <span className="text-slate-400 text-[11px]">Algorithm:</span>
                    <span className="text-white font-medium capitalize">{m.algorithm.replace('_', ' ')}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 text-[11px]">Score Metric:</span>
                    <span className="text-emerald-400 font-bold">
                      {m.metric_value !== undefined && m.metric_value !== null
                        ? m.metric_value <= 1.0
                          ? `${(m.metric_value * 100).toFixed(1)}%`
                          : m.metric_value.toFixed(3)
                        : 'Completed'}
                    </span>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500">
                      {new Date(m.created_at).toLocaleDateString()}
                    </span>
                    <Link
                      to="/explainability"
                      className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
                    >
                      Explain SHAP
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── Tab Content: Activity Timeline ──────────────────────────────── */}
      {activeTab === 'timeline' && (
        <div className="glass border border-slate-700/60 rounded-2xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-white mb-6 flex items-center gap-2">
            <Activity className="w-4 h-4 text-sky-400" />
            Your Activity History
          </h3>

          {(profileSummary?.recent_activities || []).length === 0 ? (
            <div className="text-center py-10 text-slate-500 text-xs">
              No activity records found yet. Actions you perform will be logged here.
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {profileSummary?.recent_activities.map((act) => (
                <div key={act.id} className="relative group">
                  {/* Timeline dot */}
                  <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-slate-900 border-2 border-sky-400 shadow-md group-hover:scale-125 transition-transform" />

                  <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-3.5 hover:border-slate-600 transition-colors">
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <h5 className="text-xs font-semibold text-white flex items-center gap-1.5">
                        {act.title}
                      </h5>
                      <span className="text-[10px] text-slate-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(act.created_at).toLocaleString()}
                      </span>
                    </div>
                    {act.details && (
                      <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                        {act.details}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── Tab Content: Edit Profile ───────────────────────────────────── */}
      {activeTab === 'edit' && (
        <div className="glass border border-slate-700/60 rounded-2xl p-6 md:p-8 max-w-xl shadow-lg">
          <h3 className="text-base font-semibold text-white mb-1">Update Profile Info</h3>
          <p className="text-slate-400 text-xs mb-6">
            Modify your display name and data science specialty bio.
          </p>

          {editSaved && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Profile updated successfully!
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Display Name</label>
              <input
                type="text"
                required
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
              <input
                type="email"
                disabled
                value={user.email}
                className="w-full px-3 py-2 bg-slate-800/30 border border-slate-800 rounded-xl text-slate-500 text-sm cursor-not-allowed"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Email address cannot be changed.</span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Bio / Specialty</label>
              <textarea
                rows={3}
                placeholder="e.g. Lead Machine Learning Engineer specializing in Time-Series & Deep Learning"
                value={editBio}
                onChange={(e) => setEditBio(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:border-sky-500"
              />
            </div>

            <button
              type="submit"
              className="py-2.5 px-5 bg-sky-500 hover:bg-sky-400 text-white font-semibold text-xs rounded-xl shadow-lg shadow-sky-500/25 transition-all"
            >
              Save Changes
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
