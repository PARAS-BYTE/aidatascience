import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderKanban, Plus, Search, Database, FlaskConical, Box,
  ChevronRight, Calendar, Sparkles, CheckCircle2,
  Trash2, Loader2, AlertCircle
} from 'lucide-react';
import { apiService } from '../services/api';
import { Project } from '../types/api';

export const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived'>('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res = await apiService.getProjects(statusFilter === 'all' ? undefined : statusFilter);
      setProjects(res.items || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load projects', err);
      setError(err?.response?.data?.detail || 'Failed to load projects. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [statusFilter]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      setCreating(true);
      const created = await apiService.createProject({
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      });
      setNewProjectName('');
      setNewProjectDesc('');
      setIsCreateModalOpen(false);
      navigate(`/projects/${created.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create project.');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string, projectName: string) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${projectName}"? Datasets, experiments, and models linked to this project will be removed.`)) {
      return;
    }
    try {
      await apiService.deleteProject(projectId);
      setProjects(prev => prev.filter(p => p.id !== projectId));
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete project.');
    }
  };

  const filteredProjects = projects.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchSearch;
  });

  const totalProjects = projects.length;
  const activeCount = projects.filter(p => p.status === 'active').length;
  const totalDatasets = projects.reduce((acc, p) => acc + (p.datasets || 0), 0);
  const totalExperiments = projects.reduce((acc, p) => acc + (p.experiments || 0), 0);

  return (
    <div className="space-y-8 animate-fade-in max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <FolderKanban className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Projects & Workspaces
            </h1>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            Organize datasets, experiments, models, and workflows into dedicated project environments.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm hover:shadow transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <FolderKanban className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Total Projects</p>
            <p className="text-xl font-bold text-slate-900">{totalProjects}</p>
          </div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Active Workspaces</p>
            <p className="text-xl font-bold text-slate-900">{activeCount}</p>
          </div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Linked Datasets</p>
            <p className="text-xl font-bold text-slate-900">{totalDatasets}</p>
          </div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Experiments Run</p>
            <p className="text-xl font-bold text-slate-900">{totalExperiments}</p>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-2 rounded-2xl bg-white border border-slate-200/80 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search projects by name or description..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm rounded-xl border-none bg-slate-50 focus:bg-white transition-colors"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          {(['all', 'active', 'archived'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-colors ${
                statusFilter === tab
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {/* Projects Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-56 rounded-2xl skeleton" />
          ))}
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="glass-card text-center py-16 px-6 rounded-3xl border border-slate-200 shadow-sm flex flex-col items-center">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
            <FolderKanban className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">No projects found</h3>
          <p className="text-slate-500 text-sm max-w-sm mt-1 mb-6">
            {searchQuery
              ? `No results match "${searchQuery}". Try clearing your query.`
              : 'Create your first project to start grouping datasets, experiments, and trained models.'}
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Create Your First Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map(project => {
            const isArchived = project.status === 'archived';
            return (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="group relative glass-card p-6 rounded-2xl border border-slate-200/90 shadow-sm card-hover cursor-pointer flex flex-col justify-between transition-all"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs">
                        {project.name.substring(0, 2).toUpperCase()}
                      </span>
                      <span
                        className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                          isArchived
                            ? 'bg-slate-100 text-slate-600'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                        }`}
                      >
                        {project.status}
                      </span>
                    </div>

                    <button
                      onClick={e => handleDeleteProject(e, project.id, project.name)}
                      title="Delete Project"
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1">
                    {project.name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2 min-h-[32px]">
                    {project.description || 'No description provided for this workspace.'}
                  </p>

                  {/* Best Model Badge if any */}
                  {project.best_model && (
                    <div className="mt-3.5 p-2 rounded-xl bg-purple-50/70 border border-purple-100 text-[11px] text-purple-900 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                      <span className="font-semibold">{project.best_model.algorithm}</span>
                      <span className="text-purple-400">•</span>
                      <span className="text-purple-700 font-mono">
                        {Object.entries(project.best_model.metrics || {})[0]
                          ? `${Object.entries(project.best_model.metrics)[0][0]}: ${typeof Object.entries(project.best_model.metrics)[0][1] === 'number' ? (Object.entries(project.best_model.metrics)[0][1] as number).toFixed(3) : Object.entries(project.best_model.metrics)[0][1]}`
                          : 'Trained'}
                      </span>
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100">
                  <div className="grid grid-cols-3 gap-2 text-center mb-3 text-xs">
                    <div className="bg-slate-50 p-2 rounded-xl">
                      <p className="font-bold text-slate-900">{project.datasets || 0}</p>
                      <p className="text-[10px] text-slate-500 flex items-center justify-center gap-1 mt-0.5">
                        <Database className="w-3 h-3 text-blue-500" />
                        Data
                      </p>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-xl">
                      <p className="font-bold text-slate-900">{project.experiments || 0}</p>
                      <p className="text-[10px] text-slate-500 flex items-center justify-center gap-1 mt-0.5">
                        <FlaskConical className="w-3 h-3 text-amber-500" />
                        Exps
                      </p>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-xl">
                      <p className="font-bold text-slate-900">{project.models || 0}</p>
                      <p className="text-[10px] text-slate-500 flex items-center justify-center gap-1 mt-0.5">
                        <Box className="w-3 h-3 text-purple-500" />
                        Models
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                    <span className="text-blue-600 font-semibold flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                      Open
                      <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New Project Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-2xl bg-blue-50 text-blue-600">
                  <FolderKanban className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Create New Project</h3>
                  <p className="text-xs text-slate-500">Group models, data, and runs together</p>
                </div>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Q3 Customer Churn Model"
                  value={newProjectName}
                  onChange={e => setNewProjectName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Goals, target KPIs, and context for this workspace..."
                  value={newProjectDesc}
                  onChange={e => setNewProjectDesc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:border-blue-500"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 text-sm font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newProjectName.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold shadow-sm"
                >
                  {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                  Create Workspace
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
