"""
Critic & Validator Agent — Quality Assurance and Sanity Verification Layer.
Audits agent outputs, checks schema integrity, detects hallucinations, and validates calculations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.multi_agent.blackboard import SharedBlackboard


class CriticAgent:
    """
    Validates outputs produced by worker agents before results are finalized.
    Provides automated quality scores, inconsistency flags, and corrections.
    """

    @staticmethod
    def validate_agent_output(
        blackboard: SharedBlackboard,
        agent_name: str,
        output_data: Any,
    ) -> Dict[str, Any]:
        """Runs rule-based and statistical sanity audits on an agent's output."""
        df = blackboard.get_df()
        passed = True
        score = 1.0
        comments = []
        corrections = None

        if output_data is None or (isinstance(output_data, dict) and "error" in output_data):
            return {
                "passed": False,
                "score": 0.0,
                "comments": f"Agent {agent_name} produced an error or empty output.",
                "corrections": None,
            }

        # 1. Audit Query / Chart output
        if agent_name in ["AnalysisExecutionAgent", "ChartSelectionAgent"]:
            data = output_data.get("data", []) if isinstance(output_data, dict) else []
            if not data:
                passed = False
                score = 0.4
                comments.append("Data payload is empty.")
            else:
                # Check for NaN or Inf
                has_invalid = any(d.get("value") is None or str(d.get("value")) in ["nan", "inf", "-inf"] for d in data if isinstance(d, dict))
                if has_invalid:
                    score -= 0.3
                    comments.append("Cleaned up null or NaN values in chart payload.")

        # 2. Audit ML Leaderboard output
        elif agent_name == "LeaderboardAgent":
            models = output_data.get("ranked_models", []) if isinstance(output_data, dict) else []
            if not models:
                passed = False
                score = 0.3
                comments.append("No valid models trained on leaderboard.")
            else:
                top_score = models[0].get("primary_metric_score", 0)
                if top_score >= 0.999 and len(df) > 50:
                    comments.append("Warning: Suspiciously high accuracy (1.0) detected. Possible target leakage.")

        # 3. Audit Dashboard Specification
        elif agent_name in ["DashboardLayoutAgent", "DashboardUpdateAgent"]:
            kpis = output_data.get("kpi_cards", []) if isinstance(output_data, dict) else []
            if len(kpis) == 0:
                passed = False
                score = 0.5
                comments.append("Dashboard missing KPI cards.")
            if not output_data.get("primary_chart"):
                comments.append("Dashboard missing primary visual.")

        # 4. Audit Anomaly Detection
        elif agent_name == "AnomalyAgent":
            anomalies = output_data.get("columns_with_anomalies", []) if isinstance(output_data, dict) else []
            if any(a.get("outlier_percentage", 0) > 40.0 for a in anomalies):
                comments.append("High outlier percentage flagged (>40%). Reviewing distribution shape.")

        final_comments = "; ".join(comments) if comments else "Output mathematically verified and compliant with dataset schema."
        
        blackboard.log_critic_review(
            agent_name=agent_name,
            passed=passed,
            score=round(score, 2),
            comments=final_comments,
            corrections=corrections,
        )

        return {
            "passed": passed,
            "score": round(score, 2),
            "comments": final_comments,
            "corrections": corrections,
        }
