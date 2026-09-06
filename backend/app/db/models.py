import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, BigInteger, Integer, Float, DateTime,
    Enum as SQLEnum, Text, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Enums ────────────────────────────────────────────────────────────────────

class UploadStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, enum.Enum):
    PROFILING = "PROFILING"
    EDA = "EDA"
    CLEANING = "CLEANING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    TRAINING = "TRAINING"
    OPTIMIZATION = "OPTIMIZATION"
    EXPLAINABILITY = "EXPLAINABILITY"
    DEPLOYMENT = "DEPLOYMENT"
    RETRAINING = "RETRAINING"
    MONITORING = "MONITORING"
    FORECASTING = "FORECASTING"


class TaskType(str, enum.Enum):
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    REGRESSION = "regression"


class ModelStatus(str, enum.Enum):
    TRAINED = "TRAINED"
    VALIDATED = "VALIDATED"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


class DeploymentStatus(str, enum.Enum):
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class ExperimentStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), default="data_scientist", nullable=False)
    avatar = Column(String(50), default="DS", nullable=False)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="user", cascade="all, delete-orphan")
    models = relationship("MLModel", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # UPLOAD_DATASET, RUN_EDA, CLEAN_DATA, TRAIN_MODEL, etc.
    title = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)  # JSON metadata or description
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="activities")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)  # active, archived
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="project")
    models = relationship("MLModel", back_populates="project")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    upload_status = Column(SQLEnum(UploadStatus), default=UploadStatus.SUCCESS, nullable=False)
    profile_data = Column(Text, nullable=True)
    eda_data = Column(Text, nullable=True)
    cleaning_config = Column(Text, nullable=True)
    cleaned_file_path = Column(String(512), nullable=True)
    target_column = Column(String(255), nullable=True)
    task_type = Column(SQLEnum(TaskType), nullable=True)
    feature_config = Column(Text, nullable=True)
    validation_schema = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="datasets")
    project = relationship("Project", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetVersion.version")
    quality_reports = relationship("DataQualityReport", back_populates="dataset", cascade="all, delete-orphan", order_by="DataQualityReport.created_at.desc()")
    experiments = relationship("Experiment", back_populates="dataset", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="dataset", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    progress_message = Column(String(512), nullable=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=True)
    model_id = Column(String(36), ForeignKey("ml_models.id"), nullable=True)
    budget_seconds = Column(Integer, nullable=True)
    elimination_log = Column(Text, nullable=True)
    forecast_config = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    result_data = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")
    dataset = relationship("Dataset", back_populates="jobs")
    experiment = relationship("Experiment", back_populates="jobs")
    model = relationship("MLModel", back_populates="jobs")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    change_summary = Column(Text, nullable=True)  # "Cleaned 231 duplicates, imputed 4 columns"
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="versions")


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False)  # 0.0 to 100.0
    completeness_score = Column(Float, nullable=False)
    validity_score = Column(Float, nullable=False)
    uniqueness_score = Column(Float, nullable=False)
    consistency_score = Column(Float, nullable=False)
    leakage_score = Column(Float, nullable=False, default=100.0)
    summary = Column(Text, nullable=True)  # JSON summary
    details = Column(Text, nullable=False)  # Full JSON details
    recommendations = Column(Text, nullable=True)  # JSON list of remediation actions
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="quality_reports")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    target_column = Column(String(255), nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    algorithm = Column(String(100), nullable=False)
    hyperparameters = Column(Text, nullable=True)  # JSON
    preprocessing_config = Column(Text, nullable=True)  # JSON
    feature_config = Column(Text, nullable=True)  # JSON
    primary_metric = Column(String(50), nullable=True)
    metrics = Column(Text, nullable=True)  # JSON dict of all metrics
    cv_scores = Column(Text, nullable=True)  # JSON array of CV fold scores
    train_test_split = Column(Float, default=0.2, nullable=False)
    random_seed = Column(Integer, default=42, nullable=False)
    training_duration = Column(Float, nullable=True)  # seconds
    model_artifact_path = Column(String(512), nullable=True)
    preprocessing_artifact_path = Column(String(512), nullable=True)
    feature_names = Column(Text, nullable=True)  # JSON array
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="experiments")
    project = relationship("Project", back_populates="experiments")
    dataset = relationship("Dataset", back_populates="experiments")
    jobs = relationship("Job", back_populates="experiment")
    models = relationship("MLModel", back_populates="experiment", cascade="all, delete-orphan")


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=False)
    dataset_id = Column(String(36), nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    target_column = Column(String(255), nullable=False)
    algorithm = Column(String(100), nullable=False)
    hyperparameters = Column(Text, nullable=True)
    metrics = Column(Text, nullable=True)
    feature_names = Column(Text, nullable=True)
    artifact_path = Column(String(512), nullable=False)
    preprocessing_path = Column(String(512), nullable=True)
    explainability_data = Column(Text, nullable=True)
    status = Column(SQLEnum(ModelStatus), default=ModelStatus.TRAINED, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="models")
    project = relationship("Project", back_populates="models")
    experiment = relationship("Experiment", back_populates="models")
    deployments = relationship("Deployment", back_populates="model", cascade="all, delete-orphan")
    monitoring_records = relationship("MonitoringRecord", back_populates="model", cascade="all, delete-orphan")
    drift_results = relationship("DriftResult", back_populates="model", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="model")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_id = Column(String(36), ForeignKey("ml_models.id"), nullable=False)
    model_version = Column(Integer, nullable=False)
    endpoint = Column(String(512), nullable=True)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.DEPLOYING, nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    role = Column(String(20), default="champion", nullable=False)
    traffic_pct = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    model = relationship("MLModel", back_populates="deployments")


class MonitoringRecord(Base):
    __tablename__ = "monitoring_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_id = Column(String(36), ForeignKey("ml_models.id"), nullable=False)
    deployment_id = Column(String(36), nullable=True)
    input_data = Column(Text, nullable=True)  # JSON
    prediction = Column(Text, nullable=True)
    probability = Column(Float, nullable=True)
    ground_truth = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    model = relationship("MLModel", back_populates="monitoring_records")


class DriftResult(Base):
    __tablename__ = "drift_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_id = Column(String(36), ForeignKey("ml_models.id"), nullable=False)
    feature_name = Column(String(255), nullable=False)
    drift_score = Column(Float, nullable=False)
    drift_detected = Column(Boolean, default=False, nullable=False)
    method = Column(String(100), nullable=False)  # e.g., "ks_test", "psi"
    reference_stats = Column(Text, nullable=True)
    current_stats = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    model = relationship("MLModel", back_populates="drift_results")


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    messages = relationship("AgentMessage", back_populates="session", cascade="all, delete-orphan",
                            order_by="AgentMessage.created_at")


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("agent_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user", "assistant", "tool"
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)  # JSON
    tool_results = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    session = relationship("AgentSession", back_populates="messages")


# ─── New Advanced Features Models ─────────────────────────────────────────────

class Insight(Base):
    __tablename__ = "insights"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    column_name = Column(String(255), nullable=True)
    insight_type = Column(String(100), nullable=False)  # skew, high_nulls, likely_id, outlier, imbalance, high_correlation, constant
    severity = Column(String(20), nullable=False)       # low, medium, high, critical
    message = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset = relationship("Dataset", backref="insights")


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    operation = Column(String(100), nullable=False)  # impute_median, impute_mean, drop_duplicates, drop_column, clip_outliers, one_hot_encode, scale_standard
    params = Column(Text, nullable=True)  # JSON
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset = relationship("Dataset", backref="pipeline_steps")


class ModelCard(Base):
    __tablename__ = "model_cards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_id = Column(String(36), ForeignKey("ml_models.id"), nullable=False)
    content_md = Column(Text, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    model = relationship("MLModel", backref="model_card")


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    deployment_id = Column(String(36), ForeignKey("deployments.id"), nullable=False)
    input_json = Column(Text, nullable=True)
    prediction = Column(Text, nullable=True)
    actual = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    routed_role = Column(String(20), default="champion", nullable=False)  # champion | challenger
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    deployment = relationship("Deployment", backref="prediction_logs")


class BlackboardEvent(Base):
    __tablename__ = "blackboard_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    event_type = Column(String(20), nullable=False)  # write, read, review_gate
    status = Column(String(20), default="approved", nullable=False)  # pending_approval, approved, rejected, edited
    payload = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExperimentEmbedding(Base):
    __tablename__ = "experiment_embeddings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=False)
    summary_text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON list of floats
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    experiment = relationship("Experiment", backref="embedding_record")


class AgentPlugin(Base):
    __tablename__ = "agent_plugins"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_id = Column(String(36), ForeignKey("ml_models.id"), nullable=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # info, warning, critical
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
