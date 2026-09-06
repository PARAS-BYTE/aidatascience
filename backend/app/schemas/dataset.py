from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.db.models import UploadStatus


class DatasetBase(BaseModel):
    original_filename: str
    file_size: int
    file_type: str


class DatasetCreate(DatasetBase):
    stored_filename: str
    file_path: str
    upload_status: UploadStatus = UploadStatus.SUCCESS


class DatasetResponse(DatasetBase):
    id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    stored_filename: str
    upload_status: UploadStatus
    target_column: Optional[str] = None
    task_type: Optional[str] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetListResponse(BaseModel):
    total: int
    items: list[DatasetResponse]


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    filename: str
    total_rows: int
    total_columns: int
    columns: List[str]
    dtypes: Dict[str, str]
    rows: List[Dict[str, Any]]
    limit: int
    offset: int


# ─── Profiler Schemas ────────────────────────────────────────────────

class ColumnProfile(BaseModel):
    name: str
    dtype: str
    detected_type: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    unique_percentage: float
    sample_value: Optional[str] = None


class DataQualityOverview(BaseModel):
    missing_cells: int
    missing_percentage: float
    duplicates: int
    duplicate_percentage: float


class ColumnTypesOverview(BaseModel):
    numerical: int
    categorical: int
    date: int
    boolean: int
    other: int


class DatasetOverview(BaseModel):
    rows: int
    columns: int


class DatasetProfileResponse(BaseModel):
    dataset_id: str
    filename: str
    overview: DatasetOverview
    column_types: ColumnTypesOverview
    data_quality: DataQualityOverview
    potential_ids: List[str]
    columns: List[ColumnProfile]


# ─── EDA Schemas ─────────────────────────────────────────────────────

class NumericalStat(BaseModel):
    column: str
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    q1: float
    q3: float
    skew: float
    kurtosis: float
    unique: int
    missing: int
    missing_pct: float


class CategoricalStat(BaseModel):
    column: str
    count: int
    unique: int
    top_value: Optional[str] = None
    top_frequency: int = 0
    top_categories: List[Dict[str, Any]] = []
    missing: int = 0
    missing_pct: float = 0.0


class EDAResponse(BaseModel):
    dataset_id: str
    numerical_stats: List[Dict[str, Any]]
    categorical_stats: List[Dict[str, Any]]
    distributions: Dict[str, Any]
    correlation: Dict[str, Any]
    target_distribution: Optional[Dict[str, Any]] = None
    observations: List[Dict[str, Any]]
    shape: Dict[str, int]


# ─── Cleaning Schemas ────────────────────────────────────────────────

class CleaningIssues(BaseModel):
    total_missing: int
    missing_percentage: float
    missing_details: List[Dict[str, Any]]
    duplicates: int
    duplicate_percentage: float
    constant_columns: List[str]
    potential_ids: List[str]
    outlier_columns: List[Dict[str, Any]]
    rows: int
    columns: int


class CleaningRequest(BaseModel):
    target: str
    drop_ids: bool = True
    drop_constants: bool = True
    remove_duplicates: bool = True
    handle_missing: str = "auto"


class CleaningResponse(BaseModel):
    dataset_id: str
    steps: List[Dict[str, Any]]
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    remaining_columns: List[str]


# ─── Task Detection Schemas ─────────────────────────────────────────

class TargetSuggestion(BaseModel):
    column: str
    confidence: float
    reasons: List[str]
    dtype: str
    n_unique: int
    sample_values: List[str]


class TaskDetectionResponse(BaseModel):
    task: Optional[str] = None
    target: str
    confidence: float
    n_classes: Optional[int] = None
    class_distribution: Optional[Dict[str, int]] = None
    stats: Optional[Dict[str, float]] = None
    recommendation: Optional[str] = None
    error: Optional[str] = None


# ─── Experiment Schemas ──────────────────────────────────────────────

class TrainingRequest(BaseModel):
    dataset_id: str
    target: str
    primary_metric: Optional[str] = None
    test_size: float = 0.2
    cv_folds: int = 5
    random_seed: int = 42
    enable_feature_engineering: bool = True
    budget_seconds: Optional[int] = None


class ExperimentResponse(BaseModel):
    id: str
    name: str
    dataset_id: str
    target_column: str
    task_type: str
    algorithm: str
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    cv_scores: Optional[Dict[str, Any]] = None
    primary_metric: Optional[str] = None
    training_duration: Optional[float] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    rank: int
    algorithm: str
    display_name: str
    metrics: Dict[str, float]
    primary_metric_value: float
    training_duration: float
    status: str
    experiment_id: Optional[str] = None
    created_at: Optional[str] = None


class LeaderboardResponse(BaseModel):
    dataset_id: str
    target: str
    task_type: str
    primary_metric: str
    entries: List[LeaderboardEntry]


# ─── Optimization Schemas ───────────────────────────────────────────

class OptimizationRequest(BaseModel):
    experiment_id: str
    algorithm: str
    metric: Optional[str] = None
    n_trials: int = 50
    timeout: int = 300


class OptimizationResponse(BaseModel):
    algorithm: str
    best_score: float
    best_params: Dict[str, Any]
    n_trials_completed: int
    n_trials_failed: int
    metric: str
    duration: float
    timeout_reached: bool
    trial_history: List[Dict[str, Any]]


# ─── Model Schemas ───────────────────────────────────────────────────

class ModelResponse(BaseModel):
    id: str
    name: str
    version: int
    experiment_id: str
    dataset_id: str
    task_type: str
    target_column: str
    algorithm: str
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime
    feature_names: Optional[List[str]] = None
    sample_input: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ModelListResponse(BaseModel):
    total: int
    items: List[ModelResponse]


class PredictionRequest(BaseModel):
    features: Dict[str, Any]


class PredictionResponse(BaseModel):
    prediction: Any
    probability: Optional[float] = None
    model_id: str
    model_version: int


# ─── Deployment Schemas ──────────────────────────────────────────────

class DeploymentRequest(BaseModel):
    model_id: str
    role: Optional[str] = "champion"
    traffic_pct: Optional[float] = 1.0


class DeploymentResponse(BaseModel):
    id: str
    model_id: str
    model_version: int
    endpoint: Optional[str] = None
    status: str
    role: str = "champion"
    traffic_pct: float = 1.0
    request_count: int
    created_at: datetime
    updated_at: datetime
    model_name: Optional[str] = None
    task_type: Optional[str] = None
    target_column: Optional[str] = None
    algorithm: Optional[str] = None
    feature_names: Optional[List[str]] = None
    sample_input: Optional[Dict[str, Any]] = None
    sample_inputs: Optional[List[Dict[str, Any]]] = None
    features_schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ModelSampleInputResponse(BaseModel):
    model_id: str
    model_name: str
    algorithm: Optional[str] = None
    task_type: Optional[str] = None
    target_column: Optional[str] = None
    feature_names: List[str] = []
    sample_input: Dict[str, Any] = {}
    sample_inputs: List[Dict[str, Any]] = []
    features_schema: Dict[str, Any] = {}


class DeploymentListResponse(BaseModel):
    total: int
    items: List[DeploymentResponse]


# ─── Monitoring Schemas ──────────────────────────────────────────────

class ModelHealthResponse(BaseModel):
    model_id: str
    overall_health: str  # "healthy", "warning", "critical"
    drift_status: str  # "low", "moderate", "high"
    prediction_count: int
    drift_features: List[Dict[str, Any]]
    performance: Optional[Dict[str, Any]] = None


class DriftResultResponse(BaseModel):
    feature_name: str
    drift_score: float
    drift_detected: bool
    method: str


# ─── Evaluation Schemas ─────────────────────────────────────────────

class EvaluationResponse(BaseModel):
    metrics: Dict[str, Any]
    confusion_matrix: Optional[Dict[str, Any]] = None
    per_class_report: Optional[List[Dict[str, Any]]] = None
    roc_curve: Optional[Dict[str, Any]] = None
    pr_curve: Optional[Dict[str, Any]] = None
    scatter_data: Optional[Dict[str, Any]] = None
    residual_data: Optional[Dict[str, Any]] = None
    class_distribution: Optional[Dict[str, int]] = None
    n_samples: int = 0


# ─── Explainability Schemas ─────────────────────────────────────────

class ExplainabilityResponse(BaseModel):
    feature_importance: List[Dict[str, Any]]
    top_features: List[str]
    method: str
    n_samples_used: int
    status: str
    warning: Optional[str] = None
    error: Optional[str] = None


class PredictionExplanation(BaseModel):
    prediction: Any
    probability: Optional[float] = None
    base_value: Optional[float] = None
    contributions: List[Dict[str, Any]]
    top_positive: List[Dict[str, Any]]
    top_negative: List[Dict[str, Any]]
    status: str
    error: Optional[str] = None


# ─── Feature Engineering Schemas ─────────────────────────────────────

class FeatureEngineeringPreviewRequest(BaseModel):
    target: Optional[str] = None
    enable_date_features: bool = True
    enable_interactions: bool = True
    max_interactions: int = 5
    enable_polynomial: bool = False
    polynomial_degree: int = 2
    enable_pca: bool = False
    pca_components: int = 2
    drop_pca_original: bool = False
    preview_limit: int = 30


class FeatureEngineeringPreviewResponse(BaseModel):
    dataset_id: str
    original_shape: List[int]
    transformed_shape: List[int]
    original_columns: List[str]
    transformed_columns: List[str]
    new_features: List[str]
    steps: List[Dict[str, Any]]
    pca_report: Optional[Dict[str, Any]] = None
    target_correlations: Dict[str, float] = {}
    original_preview: List[Dict[str, Any]]
    transformed_preview: List[Dict[str, Any]]


class FeatureEngineeringApplyRequest(FeatureEngineeringPreviewRequest):
    pass


class FeatureEngineeringApplyResponse(BaseModel):
    dataset_id: str
    original_shape: List[int]
    transformed_shape: List[int]
    original_columns: List[str]
    transformed_columns: List[str]
    new_features: List[str]
    steps: List[Dict[str, Any]]
    pca_report: Optional[Dict[str, Any]] = None
    file_path: str
    status: str = "success"


# ─── Agent Schemas ───────────────────────────────────────────────────

class ChartPayload(BaseModel):
    id: Optional[str] = None
    type: str  # "bar" | "line" | "scatter" | "pie" | "area" | "histogram" | "heatmap"
    title: str
    description: Optional[str] = None
    x_key: Optional[str] = None
    y_key: Optional[str] = None
    series_keys: Optional[List[str]] = None
    data: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    dataset_id: Optional[str] = None
    guard_model: Optional[str] = None  # "meta-llama/llama-prompt-guard-2-86m" or "meta-llama/llama-prompt-guard-2-22m"
    llm_model: Optional[str] = None


class AgentChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    charts: Optional[List[ChartPayload]] = None
    guard_info: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None


class AutoPilotRequest(BaseModel):
    dataset_id: str
    target: Optional[str] = None
    llm_model: Optional[str] = None
    enable_feature_engineering: bool = True
    cv_folds: int = 5
    max_interactions: int = 5


class AutoPilotStep(BaseModel):
    step_number: int
    title: str
    status: str  # "completed" | "in_progress" | "skipped" | "failed"
    summary: str
    details: Optional[Dict[str, Any]] = None


class AutoPilotResponse(BaseModel):
    dataset_id: str
    filename: str
    target_column: str
    task_type: str
    status: str
    steps: List[AutoPilotStep]
    feature_engineering_summary: Optional[Dict[str, Any]] = None
    model_selection_reasoning: Optional[str] = None
    leaderboard: Optional[List[Dict[str, Any]]] = None
    best_model: Optional[Dict[str, Any]] = None
    feature_importance: Optional[List[Dict[str, Any]]] = None
    charts: Optional[List[ChartPayload]] = None
    executive_summary: str


# ─── Job Schemas ─────────────────────────────────────────────────────

class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    progress_message: Optional[str] = None
    dataset_id: Optional[str] = None
    experiment_id: Optional[str] = None
    model_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    total: int
    items: List[JobResponse]


# ─── Dashboard Schemas ──────────────────────────────────────────────

class DashboardStats(BaseModel):
    datasets: int = 0
    experiments: int = 0
    models: int = 0
    deployed_models: int = 0
    recent_datasets: List[Dict[str, Any]] = []
    recent_experiments: List[Dict[str, Any]] = []


# ─── Pipeline Schemas ───────────────────────────────────────────────

class PipelineStepCreate(BaseModel):
    operation: str
    params: Optional[Dict[str, Any]] = None


class PipelineStepUpdate(BaseModel):
    is_active: Optional[bool] = None
    step_order: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


class PipelineStepResponse(BaseModel):
    id: str
    dataset_id: str
    step_order: int
    operation: str
    params: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
