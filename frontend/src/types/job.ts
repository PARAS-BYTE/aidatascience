export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
export type JobType = 'TEST_JOB' | 'DATA_INGESTION' | 'DATA_ANALYSIS' | 'MODEL_TRAINING';

export interface Job {
  id: string;
  job_type: JobType;
  status: JobStatus;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  result_path?: string | null;
}

export interface JobListResponse {
  total: number;
  items: Job[];
}
