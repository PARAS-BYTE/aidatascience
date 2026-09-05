"""
Router Agent — Intent classification and task graph planning.
Analyzes user intent and selects the optimal DAG execution strategy.
"""
from typing import Dict, Any, List


class RouterAgent:
    """Classifies user requests and plans the agent DAG structure."""

    INTENT_FULL_EDA = "full_eda"
    INTENT_DASHBOARD_BUILDER = "dashboard_builder"
    INTENT_DASHBOARD_PATCH = "dashboard_patch"
    INTENT_WHY_INVESTIGATION = "why_investigation"
    INTENT_AUTOML_PREDICTION = "automl_prediction"
    INTENT_CUSTOM_QUERY = "custom_query"

    @classmethod
    def classify_intent(cls, prompt: str, has_existing_dashboard: bool = False) -> Dict[str, Any]:
        p_lower = prompt.lower().strip() if prompt else ""

        if not p_lower:
            return {"intent": cls.INTENT_FULL_EDA, "confidence": 0.95}

        # Check dashboard edit/patch on existing dashboard
        if has_existing_dashboard and any(k in p_lower for k in ["change to", "make this", "add a filter", "filter to", "remove filter", "switch to", "convert to stacked", "show me just"]):
            return {
                "intent": cls.INTENT_DASHBOARD_PATCH,
                "confidence": 0.96,
                "description": "Incremental patch to existing dashboard spec.",
            }

        # Check Why investigation
        if any(k in p_lower for k in ["why did", "why is", "root cause", "explain the drop", "explain spike", "what drove", "drivers of"]):
            return {
                "intent": cls.INTENT_WHY_INVESTIGATION,
                "confidence": 0.94,
                "description": "Multi-dimensional parallel root-cause decomposition.",
            }

        # Check ML / AutoML / Prediction
        if any(k in p_lower for k in ["predict", "train", "model", "automl", "classify", "regression", "forecast", "cluster", "detect anomalies", "machine learning"]):
            return {
                "intent": cls.INTENT_AUTOML_PREDICTION,
                "confidence": 0.93,
                "description": "Parallel machine learning pipeline and model leaderboard.",
            }

        # Check Dashboard request
        if any(k in p_lower for k in ["dashboard", "power bi", "kpi", "overview", "executive report", "visual report"]):
            return {
                "intent": cls.INTENT_DASHBOARD_BUILDER,
                "confidence": 0.92,
                "description": "Full Power BI-style self-assembling dashboard.",
            }

        # Check EDA or general analysis
        if any(k in p_lower for k in ["analyze", "eda", "explore", "quality", "profile", "statistics", "dataset"]):
            return {
                "intent": cls.INTENT_FULL_EDA,
                "confidence": 0.90,
                "description": "Comprehensive exploratory data analysis and profiling.",
            }

        # Default query / chart
        return {
            "intent": cls.INTENT_CUSTOM_QUERY,
            "confidence": 0.85,
            "description": "Specific query planner, aggregation, and chart generation.",
        }
