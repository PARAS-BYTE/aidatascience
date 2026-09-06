export interface HealthResponse {
  status: string;
  service: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string;
  };
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  avatar: string;
  bio?: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserActivity {
  id: string;
  action: string;
  title: string;
  details?: string;
  created_at: string;
}

export interface UserStats {
  datasets_count: number;
  total_storage_bytes: number;
  models_count: number;
  experiments_count: number;
  jobs_count: number;
  best_accuracy?: number;
}

export interface UploadedDatasetSummary {
  id: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  upload_status: string;
  rows?: number;
  columns?: number;
  created_at: string;
  target_column?: string;
  task_type?: string;
}

export interface TrainedModelSummary {
  id: string;
  name: string;
  algorithm: string;
  task_type: string;
  target_column: string;
  metric_value?: number;
  status: string;
  created_at: string;
}

export interface UserProfileSummary {
  user: User;
  stats: UserStats;
  uploaded_datasets: UploadedDatasetSummary[];
  trained_models: TrainedModelSummary[];
  recent_activities: UserActivity[];
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  datasets?: number;
  experiments?: number;
  completed_experiments?: number;
  models?: number;
  best_model?: {
    algorithm: string;
    metrics: Record<string, any>;
    experiment_id: string;
  } | null;
}

export interface ProjectStats extends Project {
  project_id: string;
}

export interface DatasetVersionItem {
  id: string;
  version: number;
  file_size: number;
  row_count?: number;
  column_count?: number;
  change_summary?: string;
  created_at: string;
}

export interface DatasetVersionsResponse {
  dataset_id: string;
  current_version: number;
  versions: DatasetVersionItem[];
}


