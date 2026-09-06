export type UploadStatus = 'SUCCESS' | 'FAILED' | 'PROCESSING';

export interface Dataset {
  id: string;
  original_filename: string;
  stored_filename: string;
  file_size: number;
  file_type: string;
  upload_status: UploadStatus;
  target_column?: string | null;
  task_type?: string | null;
  version?: number;
  project_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  total: number;
  items: Dataset[];
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  detected_type: 'numerical' | 'categorical' | 'date' | 'boolean' | 'other';
  missing_count: number;
  missing_percentage: number;
  unique_count: number;
  unique_percentage: number;
  sample_value?: string | null;
}

export interface DataQualityOverview {
  missing_cells: number;
  missing_percentage: number;
  duplicates: number;
  duplicate_percentage: number;
}

export interface ColumnTypesOverview {
  numerical: number;
  categorical: number;
  date: number;
  boolean: number;
  other: number;
}

export interface DatasetOverview {
  rows: number;
  columns: number;
}

export interface DatasetProfileResponse {
  dataset_id: string;
  filename: string;
  overview: DatasetOverview;
  column_types: ColumnTypesOverview;
  data_quality: DataQualityOverview;
  potential_ids: string[];
  columns: ColumnProfile[];
}
