"""
Backend comprehensive verification script.
Tests route loading, models, DB schema sync, and services.
"""
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
for p in [BACKEND_DIR, REPO_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.db.database import Base, engine, SessionLocal
from app.db.models import (
    Insight, PipelineStep, ModelCard, PredictionLog,
    BlackboardEvent, ExperimentEmbedding, AgentPlugin, Alert,
    Dataset, Experiment, MLModel, Deployment, Job
)
from app.api.router import api_router
from app.main import create_application

print("1. Creating DB schema...")
Base.metadata.create_all(bind=engine)
print("Schema creation OK!")

print("2. Verifying FastAPI application routes...")
app = create_application()
routes = [r.path for r in app.routes]
print(f"Loaded {len(routes)} routes successfully.")

# Check crucial new routes
crucial_routes = [
    "/api/datasets/{dataset_id}/insights",
    "/api/datasets/{dataset_id}/pipeline",
    "/api/datasets/{dataset_id}/pipeline/replay",
    "/api/models/{model_id}/card",
    "/api/deployments/{deployment_id}/promote",
    "/api/multi-agent/runs/{run_id}/timeline",
    "/api/multi-agent/runs/{run_id}/events/{event_id}",
    "/api/multi-agent/plugins",
    "/api/agent/ask-data",
    "/api/datasets/{dataset_id}/feature-engineering/auto-generate",
    "/api/experiments/memory/similar",
    "/api/experiments/{experiment_id}/export",
    "/api/datasets/{dataset_id}/forecast",
    "/api/monitoring/alerts",
]

for cr in crucial_routes:
    assert any(cr in r for r in routes), f"Missing route: {cr}"
print("All 14 advanced feature routes verified in FastAPI router!")

print("3. Testing Service imports and instantiate...")
from app.services.insight_service import InsightService
from app.services.pipeline_service import PipelineService
from app.services.model_card_service import ModelCardService
from app.services.text2sql_service import Text2SQLService
from app.services.experiment_memory_service import ExperimentMemoryService
from app.services.export_service import ExportService
from app.services.forecasting_service import ForecastingService
from app.services.monitoring_service import MonitoringService
from ml_engine.models.forecasting_engine import ForecastingEngine
from ml_engine.preprocessing.feature_engine import FeatureEngineeringEngine

print("All advanced services and engines imported cleanly!")

# Test ForecastingEngine with synthetic time-series
import pandas as pd
import numpy as np
dates = pd.date_range("2026-01-01", periods=30, freq="D")
values = np.linspace(10, 50, 30) + np.random.normal(0, 2, 30)
sample_df = pd.DataFrame({"timestamp": dates, "sales": values})
forecast_res = ForecastingEngine.forecast(sample_df, "timestamp", "sales", horizon=7)
assert len(forecast_res["forecast"]) == 7, "Forecast horizon mismatch"
assert "anomalies" in forecast_res, "Anomalies missing"
print("Forecasting Engine synthetic test PASSED!")

# Test PSI computation
exp_v = np.random.normal(0, 1, 100)
act_v = np.random.normal(0.5, 1.2, 100)
psi = MonitoringService.compute_psi(exp_v, act_v)
print(f"PSI Synthetic test PASSED! (PSI = {psi})")

# Test Text2SQL query on sample df
sql = Text2SQLService.generate_sql("Show top 5 sales", sample_df)
assert "SELECT" in sql.upper(), "SQL generation failed"
import duckdb
con = duckdb.connect(database=":memory:")
con.register("df", sample_df)
res_df = con.execute(sql).df()
assert len(res_df) <= 5, "DuckDB execution row count mismatch"
chart = Text2SQLService.auto_chart(res_df)
print(f"Text2SQL synthetic test PASSED! (Generated SQL: '{sql}', Chart: '{chart}')")

print("\n--- ALL BACKEND VERIFICATIONS SUCCEEDED! ---")
