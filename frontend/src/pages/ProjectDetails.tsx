import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  FolderKanban, Database, FlaskConical, Box, Activity, Settings,
  Upload, Sparkles, ChevronLeft, Calendar, CheckCircle2, Clock,
  History, ArrowUpRight, Trash2, AlertCircle, Loader2, BarChart2, ShieldCheck
} from 'lucide-react';
import { apiService } from '../services/api';
import { ProjectStats, DatasetVersionsResponse } from '../types/api';

export const ProjectDetails: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<ProjectStats | null>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [experiments, setExperiments] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'datasets' | 'experiments' | 'models' | 'activity' | 'settings'>('overview');

  // Version History Modal
  const [selectedDatasetVersions, setSelectedDatasetVersions] = useState<DatasetVersionsResponse | null>(null);

  // Upload to Project state
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit Project Settings State
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editStatus, setEditStatus] = useState('active');
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);

  const loadProjectData = async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      const [projData, dsData, expData, modelData, actData] = await Promise.all([
        apiService.getProject(projectId),
        apiService.getProjectDatasets(projectId).catch(() => ({ items: [] })),
        apiService.getProjectExperiments(projectId).catch(() => ({ items: [] })),
        apiService.getProjectModels(projectId).catch(() => ({ items: [] })),
        apiService.getProjectActivity(projectId).catch(() => []),
      ]);

      setProject(projData);
      setEditName(projData.name);
      setEditDesc(projData.description || '');
      setEditStatus(projData.status || 'active');

      setDatasets(dsData.items || []);
      setExperiments(expData.items || []);
      setModels(modelData.items || []);
      setActivities(Array.isArray(actData) ? actData : []);
    } catch (err) {
      console.error('Failed to load project details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !projectId) return;
    try {
      setUploading(true);
      await apiService.uploadDatasetToProject(file, projectId);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadProjectData();
      setActiveTab('datasets');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to upload dataset to this project.');
    } finally {
      setUploading(false);
    }
  };

  const handleViewVersions = async (datasetId: string) => {
    try {
      const res = await apiService.getDatasetVersions(datasetId);
      setSelectedDatasetVersions(res);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to fetch dataset version history.');
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) return;
    try {
      setSavingSettings(true);
      const updated = await apiService.updateProject(projectId, {
        name: editName,
        description: editDesc,
        status: editStatus,
      });
      setProject(prev => (prev ? { ...prev, ...updated } : null));
      setSettingsSaved(true);
      setTimeout(() => setSettingsSaved(false), 3000);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update project settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectId || !project) return;
    if (!window.confirm(`Are you sure you want to permanently delete workspace "${project.name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await apiService.deleteProject(projectId);
      navigate('/projects');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete project.');
    }
  };

  if (loading && !project) {
    return (
      <div className="max-w-7xl mx-auto py-12 space-y-6">
        <div className="h-8 w-48 skeleton" />
        <div className="h-44 rounded-3xl skeleton" />
        <div className="h-64 rounded-3xl skeleton" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-lg mx-auto text-center py-20">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-slate-900">Project Not Found</h2>
        <p className="text-sm text-slate-500 mt-2 mb-6">The requested workspace could not be found or you do not have permission to view it.</p>
        <Link to="/projects" className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold">
          Return to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-7xl mx-auto pb-16">
      {/* Breadcrumb & Top Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Link to="/projects" className="hover:text-blue-600 flex items-center gap-1 font-medium">
            <ChevronLeft className="w-4 h-4" />
            Projects
          </Link>
          <span>/</span>
          <span className="font-semibold text-slate-900">{project.name}</span>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".csv,.xlsx,.xls,.parquet"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all"
          >
            {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
            Upload to Project
          </button>
        </div>
      </div>

      {/* Project Banner Header */}
      <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200/90 shadow-sm relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-sm">
                {project.name.substring(0, 2).toUpperCase()}
              </span>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                {project.name}
              </h1>
              <span
                className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                  project.status === 'archived'
                    ? 'bg-slate-100 text-slate-600'
                    : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                }`}
              >
                {project.status}
              </span>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed">
              {project.description || 'No description added for this project workspace.'}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1 font-medium">
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Created {new Date(project.created_at).toLocaleDateString()}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Updated {new Date(project.updated_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          {/* Best Model Banner if available */}
          {project.best_model && (
            <div className="p-4 rounded-2xl bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-100 text-purple-900 shrink-0 min-w-[240px]">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-purple-700 mb-1">
                <Sparkles className="w-3.5 h-3.5" />
                Champion Model
              </div>
              <p className="text-base font-extrabold text-slate-900">{project.best_model.algorithm}</p>
              <div className="mt-2 pt-2 border-t border-purple-200/60 text-xs font-mono text-purple-800 space-y-0.5">
                {Object.entries(project.best_model.metrics || {}).slice(0, 2).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-purple-600 uppercase text-[10px]">{k}:</span>
                    <span className="font-bold">{typeof v === 'number' ? v.toFixed(4) : String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Workspace Quick Metric Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-slate-100">
          <div className="bg-slate-50/80 p-3 rounded-2xl">
            <p className="text-xs text-slate-500 font-medium flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-blue-600" />
              Datasets
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{datasets.length}</p>
          </div>
          <div className="bg-slate-50/80 p-3 rounded-2xl">
            <p className="text-xs text-slate-500 font-medium flex items-center gap-1.5">
              <FlaskConical className="w-3.5 h-3.5 text-amber-600" />
              Experiments
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{experiments.length}</p>
          </div>
          <div className="bg-slate-50/80 p-3 rounded-2xl">
            <p className="text-xs text-slate-500 font-medium flex items-center gap-1.5">
              <Box className="w-3.5 h-3.5 text-purple-600" />
              Trained Models
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{models.length}</p>
          </div>
          <div className="bg-slate-50/80 p-3 rounded-2xl">
            <p className="text-xs text-slate-500 font-medium flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-600" />
              Activity Events
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{activities.length}</p>
          </div>
        </div>
      </div>

      {/* Workspace Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 overflow-x-auto pb-px">
        {[
          { id: 'overview', label: 'Overview', icon: FolderKanban },
          { id: 'datasets', label: `Datasets (${datasets.length})`, icon: Database },
          { id: 'experiments', label: `Experiments (${experiments.length})`, icon: FlaskConical },
          { id: 'models', label: `Models (${models.length})`, icon: Box },
          { id: 'activity', label: 'Activity Timeline', icon: Activity },
          { id: 'settings', label: 'Settings', icon: Settings },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 whitespace-nowrap transition-colors ${
                isActive
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Quick Actions Card */}
            <div className="md:col-span-2 glass-card p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900">Project Workflow Pipeline</h3>
              <p className="text-xs text-slate-500">Fast track common operations directly scoped to this project workspace.</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-4 rounded-2xl bg-blue-50/60 hover:bg-blue-50 border border-blue-100/80 text-left transition-all group flex items-start gap-3"
                >
                  <div className="p-2 rounded-xl bg-blue-600 text-white">
                    <Upload className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">Upload Dataset</h4>
                    <p className="text-xs text-slate-500 mt-0.5">Add CSV, Excel, or Parquet directly into this workspace</p>
                  </div>
                </button>

                <button
                  onClick={() => navigate('/eda')}
                  className="p-4 rounded-2xl bg-amber-50/60 hover:bg-amber-50 border border-amber-100/80 text-left transition-all group flex items-start gap-3"
                >
                  <div className="p-2 rounded-xl bg-amber-600 text-white">
                    <BarChart2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 group-hover:text-amber-600 transition-colors">Run Exploratory EDA</h4>
                    <p className="text-xs text-slate-500 mt-0.5">Analyze distributions, correlations, and anomalies</p>
                  </div>
                </button>

                <button
                  onClick={() => navigate('/cleaning')}
                  className="p-4 rounded-2xl bg-emerald-50/60 hover:bg-emerald-50 border border-emerald-100/80 text-left transition-all group flex items-start gap-3"
                >
                  <div className="p-2 rounded-xl bg-emerald-600 text-white">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">Clean & Transform</h4>
                    <p className="text-xs text-slate-500 mt-0.5">Impute missing, detect leaks, and bump dataset version</p>
                  </div>
                </button>

                <button
                  onClick={() => navigate('/experiments')}
                  className="p-4 rounded-2xl bg-purple-50/60 hover:bg-purple-50 border border-purple-100/80 text-left transition-all group flex items-start gap-3"
                >
                  <div className="p-2 rounded-xl bg-purple-600 text-white">
                    <FlaskConical className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 group-hover:text-purple-600 transition-colors">Train AutoML Models</h4>
                    <p className="text-xs text-slate-500 mt-0.5">Evaluate multiple algorithms and optimize hyperparameters</p>
                  </div>
                </button>
              </div>
            </div>

            {/* Mini Activity Feed */}
            <div className="glass-card p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900">Recent Workspace Activity</h3>
                <button
                  onClick={() => setActiveTab('activity')}
                  className="text-xs text-blue-600 hover:text-blue-700 font-semibold"
                >
                  View All
                </button>
              </div>

              {activities.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs">
                  No activity recorded yet for this project.
                </div>
              ) : (
                <div className="space-y-3">
                  {activities.slice(0, 5).map((act, i) => (
                    <div key={i} className="flex items-start gap-3 text-xs">
                      <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                      <div>
                        <p className="font-semibold text-slate-800">{act.title || act.action}</p>
                        <p className="text-slate-400 text-[10px] mt-0.5">
                          {new Date(act.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Datasets & Version History */}
      {activeTab === 'datasets' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">
              Datasets Tagged to Workspace ({datasets.length})
            </h3>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-semibold shadow-sm"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload Dataset
            </button>
          </div>

          {datasets.length === 0 ? (
            <div className="glass-card text-center py-16 px-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col items-center">
              <Database className="w-12 h-12 text-slate-300 mb-3" />
              <h4 className="text-base font-bold text-slate-800">No Datasets in this Project</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">
                Upload a dataset or assign existing datasets to this project workspace.
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-xl"
              >
                Upload to Project
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {datasets.map(ds => (
                <div
                  key={ds.id}
                  className="glass-card p-5 rounded-2xl border border-slate-200/90 shadow-sm flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="p-2 rounded-xl bg-blue-50 text-blue-600">
                          <Database className="w-4 h-4" />
                        </span>
                        <div>
                          <h4 className="text-sm font-bold text-slate-900 line-clamp-1">
                            {ds.original_filename}
                          </h4>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {(ds.file_size / (1024 * 1024)).toFixed(2)} MB • {ds.file_type}
                          </span>
                        </div>
                      </div>

                      {/* Dataset Version Badge */}
                      <span className="px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-[10px] font-bold">
                        v{ds.version || 1}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-slate-500 mt-3 pt-3 border-t border-slate-100">
                      <span>Target: <strong className="text-slate-800">{ds.target_column || 'None'}</strong></span>
                      <span>•</span>
                      <span>Task: <strong className="text-slate-800">{ds.task_type || 'Unspecified'}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-100">
                    <button
                      onClick={() => handleViewVersions(ds.id)}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-600"
                    >
                      <History className="w-3.5 h-3.5 text-blue-500" />
                      Version History
                    </button>

                    <Link
                      to={`/datasets/${ds.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline"
                    >
                      Explore Dataset
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Experiments */}
      {activeTab === 'experiments' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">
              Experiments in this Workspace ({experiments.length})
            </h3>
            <button
              onClick={() => navigate('/experiments')}
              className="px-3 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-semibold"
            >
              New Experiment
            </button>
          </div>

          {experiments.length === 0 ? (
            <div className="glass-card text-center py-16 px-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col items-center">
              <FlaskConical className="w-12 h-12 text-slate-300 mb-3" />
              <h4 className="text-base font-bold text-slate-800">No Experiments Run Yet</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">
                Launch your first model training experiment with this workspace's datasets.
              </p>
              <button
                onClick={() => navigate('/experiments')}
                className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-xl"
              >
                Launch Experiment
              </button>
            </div>
          ) : (
            <div className="glass-card rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/80 border-b border-slate-200/80 text-slate-600 uppercase tracking-wider font-bold">
                  <tr>
                    <th className="px-4 py-3">Experiment Name</th>
                    <th className="px-4 py-3">Algorithm</th>
                    <th className="px-4 py-3">Task</th>
                    <th className="px-4 py-3">Target</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {experiments.map(exp => (
                    <tr key={exp.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-semibold text-slate-900">{exp.name}</td>
                      <td className="px-4 py-3 font-mono">{exp.algorithm}</td>
                      <td className="px-4 py-3">{exp.task_type}</td>
                      <td className="px-4 py-3 font-semibold">{exp.target_column}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700">
                          {exp.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {new Date(exp.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Models */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          <h3 className="text-base font-bold text-slate-900">
            Registered Models ({models.length})
          </h3>

          {models.length === 0 ? (
            <div className="glass-card text-center py-16 px-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col items-center">
              <Box className="w-12 h-12 text-slate-300 mb-3" />
              <h4 className="text-base font-bold text-slate-800">No Models Trained Yet</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Completed experiments will register models into this workspace repository.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {models.map(m => (
                <div key={m.id} className="glass-card p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-slate-900 text-sm">{m.name}</span>
                    <span className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 text-[10px] font-bold">
                      v{m.version || 1}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 font-mono">{m.algorithm}</p>
                  <p className="text-xs text-slate-600 mt-2">Target: <strong>{m.target_column}</strong></p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Activity */}
      {activeTab === 'activity' && (
        <div className="space-y-6">
          <h3 className="text-base font-bold text-slate-900">Audit & Activity Log</h3>
          {activities.length === 0 ? (
            <div className="glass-card text-center py-16 rounded-3xl border border-slate-200 shadow-sm text-slate-400 text-xs">
              No activity records available.
            </div>
          ) : (
            <div className="glass-card p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
              {activities.map((act, idx) => (
                <div key={idx} className="flex items-start gap-3.5 pb-4 border-b border-slate-100 last:border-b-0 last:pb-0">
                  <div className="p-2 rounded-xl bg-blue-50 text-blue-600 shrink-0 mt-0.5">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold text-slate-900">{act.title}</p>
                      <span className="text-[10px] text-slate-400">
                        {new Date(act.created_at).toLocaleString()}
                      </span>
                    </div>
                    {act.details && (
                      <p className="text-xs text-slate-500 mt-1">{act.details}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Settings */}
      {activeTab === 'settings' && (
        <div className="space-y-8 max-w-2xl">
          <div className="glass-card p-6 md:p-8 rounded-3xl border border-slate-200 shadow-sm space-y-5">
            <h3 className="text-base font-bold text-slate-900">Project Workspace Settings</h3>

            <form onSubmit={handleSaveSettings} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Workspace Name
                </label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={editDesc}
                  onChange={e => setEditDesc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Workspace Status
                </label>
                <select
                  value={editStatus}
                  onChange={e => setEditStatus(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm"
                >
                  <option value="active">Active (Open for runs)</option>
                  <option value="archived">Archived (Read-only)</option>
                </select>
              </div>

              <div className="pt-3 flex items-center justify-between">
                {settingsSaved ? (
                  <span className="text-xs font-bold text-emerald-600 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" /> Changes saved successfully!
                  </span>
                ) : <span />}

                <button
                  type="submit"
                  disabled={savingSettings}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold shadow-sm"
                >
                  {savingSettings && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>

          {/* Danger Zone */}
          <div className="p-6 md:p-8 rounded-3xl border border-rose-200 bg-rose-50/50 space-y-4">
            <h4 className="text-sm font-bold text-rose-800 uppercase tracking-wider">Danger Zone</h4>
            <p className="text-xs text-rose-600">
              Permanently delete this project workspace and all associated dataset references, experiments, and trained models.
            </p>
            <button
              onClick={handleDeleteProject}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-sm"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete Entire Project
            </button>
          </div>
        </div>
      )}

      {/* Dataset Version History Modal */}
      {selectedDatasetVersions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-2xl w-full shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-2xl bg-blue-50 text-blue-600">
                  <History className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Dataset Version History</h3>
                  <p className="text-xs text-slate-500">
                    Current Version: <strong className="text-blue-600 font-mono">v{selectedDatasetVersions.current_version}</strong>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDatasetVersions(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              {selectedDatasetVersions.versions.map(ver => (
                <div
                  key={ver.id}
                  className={`p-4 rounded-2xl border transition-all ${
                    ver.version === selectedDatasetVersions.current_version
                      ? 'bg-blue-50/50 border-blue-200 shadow-sm'
                      : 'bg-slate-50/60 border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-full bg-blue-600 text-white font-bold text-xs">
                        v{ver.version}
                      </span>
                      {ver.version === selectedDatasetVersions.current_version && (
                        <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">
                          Active Version
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">
                      {new Date(ver.created_at).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 font-medium mt-1">
                    {ver.change_summary || 'Dataset state snapshot'}
                  </p>

                  <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono mt-2 pt-2 border-t border-slate-200/60">
                    <span>Rows: <strong>{ver.row_count ?? '—'}</strong></span>
                    <span>Cols: <strong>{ver.column_count ?? '—'}</strong></span>
                    <span>Size: <strong>{(ver.file_size / 1024).toFixed(1)} KB</strong></span>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-4 flex justify-end">
              <button
                onClick={() => setSelectedDatasetVersions(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
