import axios from 'axios';
import { AuthResponse, User, UserProfileSummary } from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT Bearer token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('aidatascience_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const apiService = {
  // ─── Auth & User Profile ───────────────────────────────────────────
  login: (email: string, password: string): Promise<AuthResponse> =>
    api.post('/auth/login', { email, password }).then(r => r.data),
  register: (data: { name: string; email: string; password: string; bio?: string }): Promise<AuthResponse> =>
    api.post('/auth/register', data).then(r => r.data),
  getMe: (): Promise<User> =>
    api.get('/auth/me').then(r => r.data),
  getProfile: (): Promise<UserProfileSummary> =>
    api.get('/auth/profile').then(r => r.data),
  updateProfile: (data: { name?: string; bio?: string; avatar?: string }): Promise<User> =>
    api.put('/auth/profile', data).then(r => r.data),

  // ─── Health ────────────────────────────────────────────────────────
  health: () => api.get('/health').then(r => r.data),
  getHealth: () => api.get('/health').then(r => r.data),

  // ─── Dashboard ─────────────────────────────────────────────────────
  getDashboard: () => api.get('/dashboard').then(r => r.data),

  // ─── Datasets ──────────────────────────────────────────────────────
  uploadDataset: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  getDatasets: () => api.get('/datasets').then(r => r.data),
  getDatasetById: (id: string) => api.get(`/datasets/${id}`).then(r => r.data),
  deleteDataset: (id: string) => api.delete(`/datasets/${id}`).then(r => r.data),
  getDatasetProfile: (id: string) => api.get(`/datasets/${id}/profile`).then(r => r.data),
  getDatasetPreview: (
    id: string,
    limit: number = 50,
    offset: number = 0,
    search?: string,
    sortCol?: string,
    sortDir?: string
  ) => {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    params.set('offset', String(offset));
    if (search) params.set('search', search);
    if (sortCol) params.set('sort_col', sortCol);
    if (sortDir) params.set('sort_dir', sortDir);
    return api.get(`/datasets/${id}/preview?${params.toString()}`).then(r => r.data);
  },

  // ─── EDA & Insights ───────────────────────────────────────────────
  runEda: (datasetId: string, target?: string) =>
    api.post(`/datasets/${datasetId}/eda${target ? `?target=${target}` : ''}`).then(r => r.data),
  getInsights: (datasetId: string) =>
    api.get(`/datasets/${datasetId}/insights`).then(r => r.data),

  // ─── Cleaning & Reversible Pipeline ────────────────────────────────
  getCleaningIssues: (id: string) =>
    api.get(`/datasets/${id}/cleaning-issues`).then(r => r.data),
  cleanDataset: (id: string, options: any) =>
    api.post(`/datasets/${id}/clean`, options).then(r => r.data),
  previewCleaning: (id: string, options?: any) =>
    api.post(`/datasets/${id}/clean-preview`, options || {}).then(r => r.data),
  getPipeline: (datasetId: string) =>
    api.get(`/datasets/${datasetId}/pipeline`).then(r => r.data),
  addPipelineStep: (datasetId: string, step: { operation: string; params?: any }) =>
    api.post(`/datasets/${datasetId}/pipeline`, step).then(r => r.data),
  updatePipelineStep: (datasetId: string, stepId: string, data: { is_active?: boolean; step_order?: number; params?: any }) =>
    api.patch(`/datasets/${datasetId}/pipeline/${stepId}`, data).then(r => r.data),
  deletePipelineStep: (datasetId: string, stepId: string) =>
    api.delete(`/datasets/${datasetId}/pipeline/${stepId}`).then(r => r.data),
  replayPipeline: (datasetId: string) =>
    api.post(`/datasets/${datasetId}/pipeline/replay`).then(r => r.data),
  getPipelineDiff: (datasetId: string, stepId: string) =>
    api.get(`/datasets/${datasetId}/pipeline/${stepId}/diff`).then(r => r.data),
  previewFeatureEngineering: (id: string, options: any) =>
    api.post(`/datasets/${id}/feature-engineering/preview`, options).then(r => r.data),
  applyFeatureEngineering: (id: string, options: any) =>
    api.post(`/datasets/${id}/feature-engineering/apply`, options).then(r => r.data),
  autoGenerateFeatures: (id: string, target?: string) =>
    api.post(`/datasets/${id}/feature-engineering/auto-generate${target ? `?target=${target}` : ''}`).then(r => r.data),

  // ─── Task Detection ────────────────────────────────────────────────
  suggestTarget: (datasetId: string) =>
    api.get(`/datasets/${datasetId}/suggest-target`).then(r => r.data),
  detectTask: (datasetId: string, target: string) =>
    api.post(`/datasets/${datasetId}/detect-task?target=${target}`).then(r => r.data),

  // ─── Experiments ───────────────────────────────────────────────────
  trainModels: (config: any) =>
    api.post('/experiments/train', config).then(r => r.data),
  getExperiments: (datasetId?: string) =>
    api.get(`/experiments${datasetId ? `?dataset_id=${datasetId}` : ''}`).then(r => r.data),
  getExperiment: (id: string) =>
    api.get(`/experiments/${id}`).then(r => r.data),
  getLeaderboard: (datasetId: string) =>
    api.get(`/experiments/leaderboard/${datasetId}`).then(r => r.data),
  getSimilarExperiments: (query: string, topK: number = 3) =>
    api.get(`/experiments/memory/similar?query=${encodeURIComponent(query)}&top_k=${topK}`).then(r => r.data),

  // ─── Models ────────────────────────────────────────────────────────
  registerModel: (experimentId: string, name?: string) =>
    api.post(`/models/register?experiment_id=${experimentId}${name ? `&name=${name}` : ''}`).then(r => r.data),
  getModels: () => api.get('/models').then(r => r.data),
  getModel: (id: string) => api.get(`/models/${id}`).then(r => r.data),
  getModelCard: (id: string) => api.get(`/models/${id}/card`).then(r => r.data),
  updateModelStatus: (id: string, newStatus: string) =>
    api.put(`/models/${id}/status?new_status=${newStatus}`).then(r => r.data),
  predict: (modelId: string, features: Record<string, any>) =>
    api.post(`/models/${modelId}/predict`, { features }).then(r => r.data),

  // ─── Explainability ────────────────────────────────────────────────
  getExplainability: (modelId: string) =>
    api.get(`/models/${modelId}/explainability`).then(r => r.data),
  explainPrediction: (modelId: string, features: Record<string, any>) =>
    api.post(`/models/${modelId}/explain-prediction`, { features }).then(r => r.data),

  // ─── Optimization ─────────────────────────────────────────────────
  startOptimization: (config: any) =>
    api.post('/optimization', config).then(r => r.data),

  // ─── Deployments ───────────────────────────────────────────────────
  deployModel: (modelId: string, role: string = 'champion', trafficPct: number = 1.0) =>
    api.post('/deployments', { model_id: modelId, role, traffic_pct: trafficPct }).then(r => r.data),
  getDeployments: () => api.get('/deployments').then(r => r.data),
  stopDeployment: (id: string) => api.delete(`/deployments/${id}`).then(r => r.data),
  promoteChallenger: (id: string) => api.post(`/deployments/${id}/promote`).then(r => r.data),

  // ─── Monitoring & Alerts ───────────────────────────────────────────
  getModelHealth: (modelId: string) =>
    api.get(`/monitoring/${modelId}`).then(r => r.data),
  computeDrift: (modelId: string) =>
    api.post(`/monitoring/${modelId}/drift`).then(r => r.data),
  getAlerts: (modelId?: string) =>
    api.get(`/monitoring/alerts${modelId ? `?model_id=${modelId}` : ''}`).then(r => r.data),
  resolveAlert: (alertId: string) =>
    api.post(`/monitoring/alerts/${alertId}/resolve`).then(r => r.data),

  // ─── Forecasting ───────────────────────────────────────────────────
  forecastTimeSeries: (datasetId: string, config: { date_column?: string; value_column?: string; horizon?: number }) =>
    api.post(`/datasets/${datasetId}/forecast`, config).then(r => r.data),

  // ─── Export ────────────────────────────────────────────────────────
  exportExperiment: (experimentId: string, format: 'notebook' | 'script' = 'notebook') =>
    api.get(`/experiments/${experimentId}/export?format=${format}`, { responseType: 'blob' }),

  // ─── Agent & Ask Data ──────────────────────────────────────────────
  askData: (datasetId: string, question: string) =>
    api.post('/agent/ask-data', { dataset_id: datasetId, question }).then(r => r.data),
  agentChat: (message: string, sessionId?: string, datasetId?: string, guardModel?: string, llmModel?: string) =>
    api.post('/agent/chat', {
      message,
      session_id: sessionId,
      dataset_id: datasetId,
      guard_model: guardModel,
      llm_model: llmModel,
    }).then(r => r.data),
  runAutoPilot: (
    datasetId: string,
    target?: string,
    llmModel?: string,
    enableFeatureEngineering: boolean = true,
    cvFolds: number = 5,
    maxInteractions: number = 5
  ) =>
    api.post('/agent/auto-pilot', {
      dataset_id: datasetId,
      target,
      llm_model: llmModel,
      enable_feature_engineering: enableFeatureEngineering,
      cv_folds: cvFolds,
      max_interactions: maxInteractions,
    }).then(r => r.data),
  getAgentModels: () => api.get('/agent/models').then(r => r.data),

  // ─── Multi-Agent Architecture ──────────────────────────────────────
  multiAgentChat: (message: string, sessionId: string, datasetId: string, target?: string) =>
    api.post('/multi-agent/chat', {
      message,
      session_id: sessionId,
      dataset_id: datasetId,
      target,
    }).then(r => r.data),
  getMultiAgentBlackboard: (sessionId: string, datasetId?: string) =>
    api.get(`/multi-agent/blackboard/${sessionId}${datasetId ? `?dataset_id=${datasetId}` : ''}`).then(r => r.data),
  getBlackboardTimeline: (runId: string) =>
    api.get(`/multi-agent/runs/${runId}/timeline`).then(r => r.data),
  reviewBlackboardEvent: (runId: string, eventId: string, data: { status: string; edited_payload?: any }) =>
    api.patch(`/multi-agent/runs/${runId}/events/${eventId}`, data).then(r => r.data),
  getPlugins: () =>
    api.get('/multi-agent/plugins').then(r => r.data),
  togglePlugin: (pluginId: string, is_enabled: boolean) =>
    api.patch(`/multi-agent/plugins/${pluginId}`, { is_enabled }).then(r => r.data),
  runWhyInvestigation: (sessionId: string, datasetId: string, metric?: string, dimension?: string) =>
    api.post('/multi-agent/why-investigation', {
      session_id: sessionId,
      dataset_id: datasetId,
      metric,
      dimension,
    }).then(r => r.data),
  patchDashboard: (sessionId: string, datasetId: string, prompt: string) =>
    api.post('/multi-agent/dashboard/patch', {
      session_id: sessionId,
      dataset_id: datasetId,
      prompt,
    }).then(r => r.data),
  getMultiAgentStreamUrl: (sessionId: string, datasetId: string, prompt: string, target?: string) => {
    const params = new URLSearchParams();
    params.set('session_id', sessionId);
    params.set('dataset_id', datasetId);
    if (prompt) params.set('prompt', prompt);
    if (target) params.set('target', target);
    return `${API_BASE}/multi-agent/stream?${params.toString()}`;
  },

  // ─── Jobs ──────────────────────────────────────────────────────────
  getJobs: () => api.get('/jobs').then(r => r.data),
  getJob: (id: string) => api.get(`/jobs/${id}`).then(r => r.data),
  triggerTestJob: (shouldFail: boolean = false) =>
    api.post(`/jobs/test?should_fail=${shouldFail}`).then(r => r.data),

  // ─── Projects ───────────────────────────────────────────────────────
  getProjects: (statusFilter?: string) =>
    api.get(`/projects${statusFilter ? `?status_filter=${statusFilter}` : ''}`).then(r => r.data),
  getProject: (id: string) => api.get(`/projects/${id}`).then(r => r.data),
  createProject: (data: { name: string; description?: string }) =>
    api.post('/projects', data).then(r => r.data),
  updateProject: (id: string, data: { name?: string; description?: string; status?: string }) =>
    api.put(`/projects/${id}`, data).then(r => r.data),
  deleteProject: (id: string) => api.delete(`/projects/${id}`).then(r => r.data),
  getProjectActivity: (id: string, limit: number = 50) =>
    api.get(`/projects/${id}/activity?limit=${limit}`).then(r => r.data),
  getProjectDatasets: (id: string) => api.get(`/projects/${id}/datasets`).then(r => r.data),
  getProjectExperiments: (id: string) => api.get(`/projects/${id}/experiments`).then(r => r.data),
  getProjectModels: (id: string) => api.get(`/projects/${id}/models`).then(r => r.data),

  // ─── Dataset Versions & Project Upload ──────────────────────────────
  getDatasetVersions: (id: string) => api.get(`/datasets/${id}/versions`).then(r => r.data),
  uploadDatasetToProject: (file: File, projectId?: string) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/datasets/upload${projectId ? `?project_id=${projectId}` : ''}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },

  // ─── Data Quality Engine v2 ─────────────────────────────────────────
  getDataQuality: (datasetId: string, targetColumn?: string) =>
    api.get(`/datasets/${datasetId}/data-quality${targetColumn ? `?target_column=${targetColumn}` : ''}`).then(r => r.data),
  assessDataQuality: (datasetId: string, targetColumn?: string) =>
    api.post(`/datasets/${datasetId}/data-quality/assess`, { target_column: targetColumn }).then(r => r.data),
  remediateDataQuality: (
    datasetId: string,
    actions: {
      drop_columns?: string[];
      remove_duplicates?: boolean;
      impute_missing?: boolean;
      standardize_fuzzy?: boolean;
    }
  ) =>
    api.post(`/datasets/${datasetId}/data-quality/remediate`, actions).then(r => r.data),

  // ─── Statistical Analysis & Advanced EDA ─────────────────────────────
  getStatisticalTests: (datasetId: string, target?: string, columnA?: string, columnB?: string) => {
    const params = new URLSearchParams();
    if (target) params.set('target', target);
    if (columnA) params.set('column_a', columnA);
    if (columnB) params.set('column_b', columnB);
    return api.get(`/datasets/${datasetId}/statistical-tests?${params.toString()}`).then(r => r.data);
  },
  getChartRecommendation: (datasetId: string, columnA: string, columnB?: string) => {
    const params = new URLSearchParams();
    params.set('column_a', columnA);
    if (columnB) params.set('column_b', columnB);
    return api.get(`/datasets/${datasetId}/chart-recommendation?${params.toString()}`).then(r => r.data);
  },
  getAutoEdaReport: (datasetId: string, target?: string) =>
    api.get(`/datasets/${datasetId}/auto-eda-report${target ? `?target=${target}` : ''}`).then(r => r.data),

  // ─── Unsupervised Learning Suite ─────────────────────────────────────
  runClustering: (
    datasetId: string,
    options: {
      features?: string[];
      algorithm?: string;
      n_clusters?: number;
      auto_k?: boolean;
      k_min?: number;
      k_max?: number;
    } = {}
  ) => api.post(`/datasets/${datasetId}/unsupervised/cluster`, options).then(r => r.data),

  runAnomalyDetection: (
    datasetId: string,
    options: {
      features?: string[];
      algorithm?: string;
      contamination?: number;
    } = {}
  ) => api.post(`/datasets/${datasetId}/unsupervised/anomalies`, options).then(r => r.data),

  runPca: (
    datasetId: string,
    options: {
      features?: string[];
      n_components?: number;
    } = {}
  ) => api.post(`/datasets/${datasetId}/unsupervised/pca`, options).then(r => r.data),

  appendUnsupervisedColumn: (
    datasetId: string,
    options: {
      column_name: string;
      values: any[];
      change_summary?: string;
    }
  ) => api.post(`/datasets/${datasetId}/unsupervised/append-labels`, options).then(r => r.data),
};
