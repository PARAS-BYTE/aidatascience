import os
import sys

# Ensure backend and root are in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
for p in [BACKEND_DIR, BASE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import numpy as np
import pandas as pd
import asyncio

from app.services.multi_agent.blackboard import SharedBlackboard, get_blackboard
from app.services.multi_agent.dag_executor import DAGExecutor, TaskStatus
from app.services.multi_agent.agents.data_understanding_agents import (
    ProfilingAgent, DataQualityAgent, StatisticsAgent, RelationshipAgent, SemanticAgent
)
from app.services.multi_agent.agents.analysis_agents import (
    QueryPlannerAgent, AnalysisExecutionAgent, ChartSelectionAgent,
    TrendAgent, SegmentationAgent, AnomalyAgent, WhyInvestigationAgent, NarrativeAgent
)
from app.services.multi_agent.agents.dashboard_agents import (
    DashboardLayoutAgent, DashboardUpdateAgent
)
from app.services.multi_agent.agents.ml_specialist_agents import (
    ProblemFramingAgent, FeatureEngineeringAgent,
    ClassificationAgent, RegressionAgent, ClusteringAgent,
    AnomalyModelAgent, DimensionalityReductionAgent,
    LeaderboardAgent, ExplainabilityAgent
)
from app.services.multi_agent.agents.critic_agent import CriticAgent
from app.services.multi_agent.agents.router_agent import RouterAgent


@pytest.fixture
def sample_sales_df():
    """Generates a synthetic sales/customer churn dataset for testing."""
    np.random.seed(42)
    n = 100
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Furniture", "Apparel", "Office"]
    
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    revenue = np.random.uniform(100, 1000, size=n)
    cost = revenue * np.random.uniform(0.5, 0.9, size=n)
    churn = np.random.choice([0, 1], size=n, p=[0.75, 0.25])
    
    # Add an anomaly
    revenue[15] = 9999.0

    df = pd.DataFrame({
        "order_id": [f"ORD_{i:04d}" for i in range(n)],
        "order_date": dates,
        "region": np.random.choice(regions, size=n),
        "category": np.random.choice(categories, size=n),
        "revenue": revenue,
        "cost": cost,
        "units_sold": np.random.randint(1, 20, size=n),
        "churn": churn,
    })
    return df


def test_blackboard_operations(sample_sales_df):
    """Test blackboard setting, getting, and snapshotting."""
    bb = SharedBlackboard(session_id="test_session", dataset_id="test_dataset")
    bb.set_df(sample_sales_df)
    assert bb.get_df() is not None
    assert len(bb.get_df()) == 100

    bb.set("test_key", {"metric": 42}, agent_name="TestAgent")
    assert bb.has("test_key")
    assert bb.get("test_key") == {"metric": 42}
    
    snap = bb.snapshot()
    assert snap["session_id"] == "test_session"
    assert "test_key" in snap["keys_present"]


def test_parallel_data_understanding_agents(sample_sales_df):
    """Test concurrent execution of data understanding agents."""
    bb = SharedBlackboard(session_id="test_eda", dataset_id="test_dataset")
    bb.set_df(sample_sales_df)

    p_res = ProfilingAgent.run(bb)
    assert p_res["row_count"] == 100
    assert p_res["column_count"] == 8

    q_res = DataQualityAgent.run(bb)
    assert "quality_score" in q_res
    assert q_res["quality_score"] > 50

    s_res = StatisticsAgent.run(bb)
    assert "revenue" in s_res["summary"]

    r_res = RelationshipAgent.run(bb)
    assert "candidate_keys" in r_res

    sem_res = SemanticAgent.run(bb)
    assert "revenue" in sem_res["metric_columns"]
    assert "region" in sem_res["dimension_columns"]


def test_analysis_and_dashboard_agents(sample_sales_df):
    """Test query, trend, segmentation, anomaly, narrative, and dashboard agents."""
    bb = SharedBlackboard(session_id="test_dash", dataset_id="test_dataset")
    bb.set_df(sample_sales_df)
    SemanticAgent.run(bb)

    # Trend & Anomaly
    trend_res = TrendAgent.run(bb)
    assert "trends" in trend_res
    
    anom_res = AnomalyAgent.run(bb)
    assert anom_res["total_anomalies_detected"] >= 1  # Our injected 9999.0 revenue

    seg_res = SegmentationAgent.run(bb)
    assert "segments" in seg_res

    narr_res = NarrativeAgent.run(bb)
    assert len(narr_res["insights"]) >= 3

    # Dashboard Layout
    dash_spec = DashboardLayoutAgent.run(bb, title="Test Sales Dashboard")
    assert len(dash_spec["kpi_cards"]) >= 2
    assert dash_spec["primary_chart"] is not None
    assert dash_spec["cross_filtering_enabled"] is True

    # Dashboard Update Agent (patch)
    updated_spec = DashboardUpdateAgent.run(bb, prompt="change primary chart to stacked bar")
    assert updated_spec["primary_chart"]["type"] == "stacked_bar"


def test_why_investigation_agent(sample_sales_df):
    """Test parallel dimension root-cause decomposition."""
    bb = SharedBlackboard(session_id="test_why", dataset_id="test_dataset")
    bb.set_df(sample_sales_df)
    SemanticAgent.run(bb)

    why_res = WhyInvestigationAgent.run(bb, metric="revenue")
    assert why_res["target_metric"] == "revenue"
    assert len(why_res["dimension_breakdowns"]) >= 1


def test_ml_specialist_agents(sample_sales_df):
    """Test ML framing, feature engineering, classification, regression, and explainability."""
    bb = SharedBlackboard(session_id="test_ml", dataset_id="test_dataset")
    bb.set_df(sample_sales_df)
    SemanticAgent.run(bb)

    # Problem Framing for churn
    framing = ProblemFramingAgent.run(bb, user_goal="predict churn", target_col="churn")
    assert framing["task_type"] == "classification"

    # Feature Engineering
    fe_res = FeatureEngineeringAgent.run(bb)
    assert fe_res["processed_features_count"] >= 3

    # Classification
    clf_res = ClassificationAgent.run(bb)
    assert len(clf_res["models_evaluated"]) == 3

    # Leaderboard
    lb = LeaderboardAgent.run(bb)
    assert len(lb["ranked_models"]) >= 1

    # Explainability
    exp = ExplainabilityAgent.run(bb)
    assert len(exp["feature_importances"]) >= 1


def test_dag_executor_parallel_execution(sample_sales_df):
    """Test DAG execution engine and task dependency resolution."""
    async def _async_runner():
        bb = SharedBlackboard(session_id="test_dag", dataset_id="test_dataset")
        bb.set_df(sample_sales_df)

        executor = DAGExecutor(blackboard=bb)
        
        # Layer 1: Parallel
        executor.add_node("prof", "ProfilingAgent", "Profile", ProfilingAgent.run, category="understanding")
        executor.add_node("qual", "DataQualityAgent", "Quality", DataQualityAgent.run, category="understanding")
        executor.add_node("sem", "SemanticAgent", "Semantics", SemanticAgent.run, category="understanding")
        
        # Layer 2: Depends on Semantics
        executor.add_node("trend", "TrendAgent", "Trend", TrendAgent.run, dependencies=["sem"], category="analysis")
        
        # Layer 3: Layout depends on Trend
        executor.add_node("dash", "DashboardLayoutAgent", "Dashboard", DashboardLayoutAgent.run, dependencies=["trend"], category="dashboard")

        result = await executor.execute_all()
        assert len(result["completed_nodes"]) == 5
        assert len(result["failed_nodes"]) == 0
        assert bb.has("dashboard_spec")

    asyncio.run(_async_runner())
