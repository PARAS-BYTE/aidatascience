"""
Master Multi-Agent Orchestrator — Coordinates task graph planning, parallel execution,
shared blackboard synchronization, Critic validation, and SSE streaming.
"""
import os
import time
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import Dataset
from app.services.multi_agent.blackboard import SharedBlackboard, get_blackboard
from app.services.multi_agent.dag_executor import DAGExecutor, TaskStatus
from app.services.multi_agent.agents.router_agent import RouterAgent
from app.services.multi_agent.agents.critic_agent import CriticAgent
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


class MultiAgentOrchestrator:
    """Central orchestrator for the multi-agent system."""

    @classmethod
    def load_dataset_to_blackboard(cls, db: Session, dataset_id: str, blackboard: SharedBlackboard) -> pd.DataFrame:
        """Loads dataset file into blackboard cache if not already loaded."""
        cached_df = blackboard.get_df()
        if cached_df is not None and not cached_df.empty:
            return cached_df

        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} record not found in database.")

        # Resolve file path across multiple candidate locations
        target_path = dataset.file_path
        if not target_path or not os.path.exists(target_path):
            candidates = [
                os.path.join(settings.UPLOAD_DIR, dataset.stored_filename) if dataset.stored_filename else None,
                os.path.join("data", "uploads", dataset.stored_filename) if dataset.stored_filename else None,
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "uploads", dataset.stored_filename) if dataset.stored_filename else None,
            ]
            found = False
            for cand in candidates:
                if cand and os.path.exists(cand):
                    target_path = cand
                    found = True
                    break
            if not found:
                raise ValueError(f"Dataset file '{dataset.stored_filename}' not found on storage disk.")

        # Robust CSV / Excel loading
        file_ext = str(dataset.file_type or "").lower()
        if file_ext == "csv" or str(target_path).lower().endswith(".csv") or str(dataset.original_filename).lower().endswith(".csv"):
            try:
                df = pd.read_csv(target_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(target_path, encoding="latin1")
        else:
            try:
                df = pd.read_excel(target_path)
            except Exception:
                try:
                    df = pd.read_csv(target_path, encoding="utf-8")
                except Exception:
                    df = pd.read_csv(target_path, encoding="latin1")

        if df is None or df.empty:
            raise ValueError(f"Dataset {dataset_id} contains no data rows.")

        blackboard.set_df(df)
        return df

    @classmethod
    def build_dag_for_intent(
        cls,
        intent: str,
        executor: DAGExecutor,
        prompt: str = "",
        target_col: Optional[str] = None,
    ) -> None:
        """Constructs task nodes and dependency edges based on routed intent."""
        blackboard = executor.blackboard

        # 1. Understanding Layer (All 5 run in parallel with NO dependencies)
        has_profile = blackboard.has("profile")
        if not has_profile or intent in [RouterAgent.INTENT_FULL_EDA, RouterAgent.INTENT_DASHBOARD_BUILDER]:
            executor.add_node(
                node_id="profiling_agent",
                agent_name="ProfilingAgent",
                display_name="Data Profiling Agent",
                description="Auditing schema, types, shape, and null ratios",
                category="understanding",
                fn=ProfilingAgent.run,
            )
            executor.add_node(
                node_id="quality_agent",
                agent_name="DataQualityAgent",
                display_name="Data Quality Agent",
                description="Detecting missing values, duplicates, and constants",
                category="understanding",
                fn=DataQualityAgent.run,
            )
            executor.add_node(
                node_id="statistics_agent",
                agent_name="StatisticsAgent",
                display_name="Statistics Agent",
                description="Calculating descriptive stats, skewness, and correlation matrix",
                category="understanding",
                fn=StatisticsAgent.run,
            )
            executor.add_node(
                node_id="relationship_agent",
                agent_name="RelationshipAgent",
                display_name="Relationship Agent",
                description="Analyzing candidate keys, cardinality, and joins",
                category="understanding",
                fn=RelationshipAgent.run,
            )
            executor.add_node(
                node_id="semantic_agent",
                agent_name="SemanticAgent",
                display_name="Semantic Understanding Agent",
                description="Inferring business meaning, currencies, and roles",
                category="understanding",
                fn=SemanticAgent.run,
            )

        # 2. Add intent-specific analysis nodes
        if intent == RouterAgent.INTENT_DASHBOARD_PATCH:
            executor.add_node(
                node_id="dashboard_update_agent",
                agent_name="DashboardUpdateAgent",
                display_name="Dashboard Update Agent",
                description="Patching active Power BI dashboard spec incrementally",
                category="dashboard",
                fn=lambda bb: DashboardUpdateAgent.run(bb, prompt=prompt),
            )

        elif intent == RouterAgent.INTENT_WHY_INVESTIGATION:
            executor.add_node(
                node_id="why_investigation_agent",
                agent_name="WhyInvestigationAgent",
                display_name="Why Investigation Agent",
                description="Decomposing metrics across multiple dimensions in parallel",
                category="analysis",
                dependencies=["semantic_agent"] if "semantic_agent" in executor.nodes else [],
                fn=WhyInvestigationAgent.run,
            )
            executor.add_node(
                node_id="narrative_agent",
                agent_name="NarrativeAgent",
                display_name="Narrative Insights Agent",
                description="Summarizing primary root cause drivers",
                category="analysis",
                dependencies=["why_investigation_agent"],
                fn=NarrativeAgent.run,
            )

        elif intent == RouterAgent.INTENT_AUTOML_PREDICTION:
            executor.add_node(
                node_id="problem_framing_agent",
                agent_name="ProblemFramingAgent",
                display_name="Problem Framing Agent",
                description="Classifying ML task and identifying optimization metric",
                category="ml",
                dependencies=["semantic_agent"] if "semantic_agent" in executor.nodes else [],
                fn=lambda bb: ProblemFramingAgent.run(bb, user_goal=prompt, target_col=target_col),
            )
            executor.add_node(
                node_id="feature_engineering_agent",
                agent_name="FeatureEngineeringAgent",
                display_name="Feature Engineering Agent",
                description="Encoding, scaling, and handling leakage prevention",
                category="ml",
                dependencies=["problem_framing_agent"],
                fn=FeatureEngineeringAgent.run,
            )
            # Parallel ML models
            executor.add_node(
                node_id="classification_agent",
                agent_name="ClassificationAgent",
                display_name="Classification Model Agent",
                description="Training Random Forest, Logistic Reg, Gradient Boosting",
                category="ml",
                dependencies=["feature_engineering_agent"],
                fn=ClassificationAgent.run,
            )
            executor.add_node(
                node_id="regression_agent",
                agent_name="RegressionAgent",
                display_name="Regression Model Agent",
                description="Training Ridge, Random Forest Regressor, Gradient Boosting",
                category="ml",
                dependencies=["feature_engineering_agent"],
                fn=RegressionAgent.run,
            )
            executor.add_node(
                node_id="clustering_agent",
                agent_name="ClusteringAgent",
                display_name="Clustering Agent",
                description="Auto-selecting optimal k and profiling cohorts",
                category="ml",
                dependencies=["feature_engineering_agent"],
                fn=ClusteringAgent.run,
            )
            executor.add_node(
                node_id="anomaly_model_agent",
                agent_name="AnomalyModelAgent",
                display_name="Unsupervised Anomaly Model Agent",
                description="Fitting Isolation Forest contamination detector",
                category="ml",
                dependencies=["feature_engineering_agent"],
                fn=AnomalyModelAgent.run,
            )
            executor.add_node(
                node_id="dim_reduction_agent",
                agent_name="DimensionalityReductionAgent",
                display_name="Dimensionality Reduction Agent",
                description="Calculating 2D PCA projection for map visualization",
                category="ml",
                dependencies=["feature_engineering_agent"],
                fn=DimensionalityReductionAgent.run,
            )
            # Fan-in: Leaderboard & Explainability
            executor.add_node(
                node_id="leaderboard_agent",
                agent_name="LeaderboardAgent",
                display_name="Leaderboard & Trade-off Agent",
                description="Ranking candidate models and synthesizing performance trade-offs",
                category="ml",
                dependencies=["classification_agent", "regression_agent"],
                fn=LeaderboardAgent.run,
            )
            executor.add_node(
                node_id="explainability_agent",
                agent_name="ExplainabilityAgent",
                display_name="Explainability (SHAP) Agent",
                description="Generating feature importance and prediction drivers",
                category="ml",
                dependencies=["leaderboard_agent"],
                fn=ExplainabilityAgent.run,
            )

        else:
            # Full EDA / Dashboard / Custom query: parallel analysis fan-out
            understanding_deps = [n for n in ["profiling_agent", "semantic_agent"] if n in executor.nodes]
            
            executor.add_node(
                node_id="trend_agent",
                agent_name="TrendAgent",
                display_name="Time-Series & Trend Agent",
                description="Detecting period-over-period growth and seasonality",
                category="analysis",
                dependencies=understanding_deps,
                fn=TrendAgent.run,
            )
            executor.add_node(
                node_id="segmentation_agent",
                agent_name="SegmentationAgent",
                display_name="Segmentation & Cohort Agent",
                description="Ranking top/bottom categorical performer segments",
                category="analysis",
                dependencies=understanding_deps,
                fn=SegmentationAgent.run,
            )
            executor.add_node(
                node_id="anomaly_agent",
                agent_name="AnomalyAgent",
                display_name="Anomaly Detection Agent",
                description="Ensemble outlier detection across numeric features",
                category="analysis",
                dependencies=understanding_deps,
                fn=AnomalyAgent.run,
            )
            executor.add_node(
                node_id="query_planner_agent",
                agent_name="QueryPlannerAgent",
                display_name="Query Planner Agent",
                description="Formulating structured aggregation query spec",
                category="analysis",
                dependencies=understanding_deps,
                fn=lambda bb: QueryPlannerAgent.run(bb, prompt=prompt),
            )
            executor.add_node(
                node_id="analysis_execution_agent",
                agent_name="AnalysisExecutionAgent",
                display_name="Analysis Execution Agent",
                description="Executing analytical queries and data grouping",
                category="analysis",
                dependencies=["query_planner_agent"],
                fn=AnalysisExecutionAgent.run,
            )
            executor.add_node(
                node_id="chart_selection_agent",
                agent_name="ChartSelectionAgent",
                display_name="Chart Selection Agent",
                description="Selecting recommended visualization format",
                category="analysis",
                dependencies=["analysis_execution_agent"],
                fn=ChartSelectionAgent.run,
            )
            executor.add_node(
                node_id="narrative_agent",
                agent_name="NarrativeAgent",
                display_name="Narrative Insights Agent",
                description="Synthesizing plain-English executive insights",
                category="analysis",
                dependencies=["trend_agent", "segmentation_agent", "anomaly_agent"],
                fn=NarrativeAgent.run,
            )
            executor.add_node(
                node_id="dashboard_layout_agent",
                agent_name="DashboardLayoutAgent",
                display_name="Power BI Dashboard Layout Agent",
                description="Generating self-assembling interactive report spec",
                category="dashboard",
                dependencies=["narrative_agent", "chart_selection_agent"],
                fn=DashboardLayoutAgent.run,
            )

        # Critic Validation Node (runs at the very end to audit everything)
        all_prior_nodes = list(executor.nodes.keys())
        executor.add_node(
            node_id="critic_validator_agent",
            agent_name="CriticAgent",
            display_name="Critic & Validator Agent",
            description="Auditing calculation integrity and chart specifications",
            category="critic",
            dependencies=all_prior_nodes,
            fn=lambda bb: CriticAgent.validate_agent_output(bb, "DashboardLayoutAgent", bb.get("dashboard_spec")),
        )

    @classmethod
    async def run_pipeline(
        cls,
        db: Session,
        session_id: str,
        dataset_id: str,
        prompt: str = "",
        target_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the complete parallel multi-agent pipeline and returns unified results."""
        blackboard = get_blackboard(session_id=session_id, dataset_id=dataset_id)
        
        # Load dataset
        cls.load_dataset_to_blackboard(db=db, dataset_id=dataset_id, blackboard=blackboard)

        has_existing_dashboard = blackboard.has("dashboard_spec")
        routing = RouterAgent.classify_intent(prompt=prompt, has_existing_dashboard=has_existing_dashboard)
        intent = routing["intent"]

        executor = DAGExecutor(blackboard=blackboard)
        cls.build_dag_for_intent(intent=intent, executor=executor, prompt=prompt, target_col=target_col)

        dag_execution_result = await executor.execute_all()

        return {
            "session_id": session_id,
            "dataset_id": dataset_id,
            "intent": intent,
            "routing": routing,
            "dag": dag_execution_result,
            "blackboard": blackboard.snapshot(),
            "dashboard_spec": blackboard.get("dashboard_spec"),
            "narrative": blackboard.get("narrative"),
            "ml_results": {
                "task": blackboard.get("ml_task"),
                "leaderboard": blackboard.get("leaderboard"),
                "explainability": blackboard.get("explainability"),
                "clustering": blackboard.get("clustering_results"),
                "anomaly": blackboard.get("anomaly_model_results"),
                "dim_reduction": blackboard.get("dim_reduction_results"),
            },
            "critic_reviews": blackboard.get_critic_logs(),
        }

    @classmethod
    async def stream_pipeline(
        cls,
        db: Session,
        session_id: str,
        dataset_id: str,
        prompt: str = "",
        target_col: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streams real-time DAG execution events over SSE."""
        blackboard = get_blackboard(session_id=session_id, dataset_id=dataset_id)
        cls.load_dataset_to_blackboard(db=db, dataset_id=dataset_id, blackboard=blackboard)

        has_existing_dashboard = blackboard.has("dashboard_spec")
        routing = RouterAgent.classify_intent(prompt=prompt, has_existing_dashboard=has_existing_dashboard)
        intent = routing["intent"]

        executor = DAGExecutor(blackboard=blackboard)
        cls.build_dag_for_intent(intent=intent, executor=executor, prompt=prompt, target_col=target_col)

        # Start execution in background task and yield events
        exec_task = asyncio.create_task(executor.execute_all())

        # Yield initial DAG topology
        yield {
            "event": "dag_initialized",
            "intent": intent,
            "routing": routing,
            "dag_spec": executor.get_dag_spec(),
        }

        while not exec_task.done():
            # Drain events from queue
            while not executor._events_queue.empty():
                event = await executor._events_queue.get()
                # Attach latest blackboard card snapshot if node completed
                if event.get("event") == "node_completed":
                    event["blackboard_snapshot"] = blackboard.snapshot()
                yield event
            await asyncio.sleep(0.05)

        # Drain any remaining events
        while not executor._events_queue.empty():
            event = await executor._events_queue.get()
            yield event

        final_result = await exec_task
        yield {
            "event": "pipeline_finished",
            "result": final_result,
            "final_blackboard": blackboard.snapshot(),
        }
