"""
EDA Auto-Insights Service — Automatically extracts actionable data quality and statistical insights.
Combines deterministic heuristic checks (skew, high nulls, cardinality, multicollinearity, imbalance)
with optional LLM narrative enrichment.
"""
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Insight, Dataset
from app.core.config import settings

logger = logging.getLogger(__name__)


class InsightService:
    @staticmethod
    def generate_insights(dataset_id: str, eda_data: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """
        Analyze EDA results and persist structured insights to DB.
        """
        insights_data: List[Dict[str, Any]] = []

        num_stats = eda_data.get("numerical_stats", [])
        cat_stats = eda_data.get("categorical_stats", [])
        correlations = eda_data.get("correlations", {})
        target_analysis = eda_data.get("target_analysis", {})

        # Total rows estimate
        total_rows = 0
        if num_stats:
            total_rows = max([s.get("count", 0) + s.get("missing", 0) for s in num_stats], default=0)
        elif cat_stats:
            total_rows = max([s.get("count", 0) + s.get("missing", 0) for s in cat_stats], default=0)

        # 1. Check Numerical Columns: Skew, Missing, Outliers, Zero-variance
        for col_stat in num_stats:
            col = col_stat.get("column")
            skew = col_stat.get("skew")
            missing_pct = col_stat.get("missing_pct", 0)
            unique = col_stat.get("unique", 0)
            std = col_stat.get("std", 1.0)
            q1 = col_stat.get("q1")
            q3 = col_stat.get("q3")
            min_val = col_stat.get("min")
            max_val = col_stat.get("max")

            # Missing values
            if missing_pct >= 40.0:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "high_nulls",
                    "severity": "critical" if missing_pct > 70 else "high",
                    "message": f"Column '{col}' has {missing_pct}% missing values.",
                    "suggested_action": f"Drop column or impute with median/KNN depending on domain relevance."
                })
            elif missing_pct >= 10.0:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "high_nulls",
                    "severity": "medium",
                    "message": f"Column '{col}' has {missing_pct}% missing values.",
                    "suggested_action": "Impute missing values using median or mean."
                })

            # Zero / Near-zero variance
            if std == 0 or unique <= 1:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "constant",
                    "severity": "high",
                    "message": f"Column '{col}' is constant with zero variance (unique={unique}).",
                    "suggested_action": "Drop this column as it carries zero predictive information."
                })

            # Skewness
            if skew is not None and abs(skew) > 1.5:
                direction = "right (positive)" if skew > 0 else "left (negative)"
                insights_data.append({
                    "column_name": col,
                    "insight_type": "skew",
                    "severity": "medium" if abs(skew) < 3.0 else "high",
                    "message": f"Column '{col}' is heavily skewed ({direction}, skew={round(skew, 2)}).",
                    "suggested_action": "Apply log, Box-Cox, or Yeo-Johnson power transformation to normalize."
                })

            # Extreme Outliers via IQR
            if q1 is not None and q3 is not None and min_val is not None and max_val is not None:
                iqr = q3 - q1
                if iqr > 0:
                    lower_bound = q1 - 3.0 * iqr
                    upper_bound = q3 + 3.0 * iqr
                    if min_val < lower_bound or max_val > upper_bound:
                        insights_data.append({
                            "column_name": col,
                            "insight_type": "outlier",
                            "severity": "medium",
                            "message": f"Column '{col}' contains severe outliers outside 3x IQR range [{round(lower_bound, 2)}, {round(upper_bound, 2)}].",
                            "suggested_action": "Consider clipping/winsorizing outliers or applying robust scaling."
                        })

            # Likely ID
            if total_rows > 50 and unique == total_rows:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "likely_id",
                    "severity": "medium",
                    "message": f"Column '{col}' has unique values for 100% of rows, indicating a primary key or index identifier.",
                    "suggested_action": "Exclude from model feature set to avoid target leakage/overfitting."
                })

        # 2. Check Categorical Columns: Cardinality, Imbalance
        for col_stat in cat_stats:
            col = col_stat.get("column")
            unique = col_stat.get("unique", 0)
            missing_pct = col_stat.get("missing_pct", 0)
            top_pct = 0.0
            if col_stat.get("top_categories") and len(col_stat["top_categories"]) > 0:
                top_pct = col_stat["top_categories"][0].get("percentage", 0.0)

            if missing_pct >= 30.0:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "high_nulls",
                    "severity": "high",
                    "message": f"Categorical column '{col}' has {missing_pct}% missing values.",
                    "suggested_action": "Impute with mode or treat missing as a distinct 'Missing' category."
                })

            if unique > 100 and total_rows > 0 and (unique / total_rows) > 0.5:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "high_cardinality",
                    "severity": "high",
                    "message": f"Column '{col}' has very high cardinality ({unique} distinct values).",
                    "suggested_action": "Use target encoding, frequency encoding, or hash embeddings instead of one-hot encoding."
                })

            if top_pct >= 95.0 and unique > 1:
                insights_data.append({
                    "column_name": col,
                    "insight_type": "imbalance",
                    "severity": "medium",
                    "message": f"Column '{col}' is dominated by a single category ({top_pct}% occurrences).",
                    "suggested_action": "Check if this feature provides sufficient variance or consider binarizing."
                })

        # 3. Check Multicollinearity from Correlation Matrix
        if isinstance(correlations, dict):
            pairs_checked = set()
            for col1, row_vals in correlations.items():
                if isinstance(row_vals, dict):
                    for col2, corr_val in row_vals.items():
                        if col1 != col2 and corr_val is not None:
                            pair_key = tuple(sorted([col1, col2]))
                            if pair_key not in pairs_checked:
                                pairs_checked.add(pair_key)
                                try:
                                    corr_float = abs(float(corr_val))
                                    if corr_float >= 0.88:
                                        insights_data.append({
                                            "column_name": f"{col1}, {col2}",
                                            "insight_type": "high_correlation",
                                            "severity": "high",
                                            "message": f"High multicollinearity between '{col1}' and '{col2}' (r = {round(float(corr_val), 2)}).",
                                            "suggested_action": "Consider dropping one of the correlated features or applying dimensionality reduction."
                                        })
                                except (ValueError, TypeError):
                                    pass

        # 4. Target analysis check
        if target_analysis and isinstance(target_analysis, dict):
            target_type = target_analysis.get("type")
            target_col = target_analysis.get("column", "Target")
            if target_type == "classification" and "class_distribution" in target_analysis:
                dist = target_analysis["class_distribution"]
                if isinstance(dist, dict) and len(dist) >= 2:
                    counts = list(dist.values())
                    max_c = max(counts)
                    min_c = min(counts)
                    ratio = (max_c / min_c) if min_c > 0 else float("inf")
                    if ratio >= 4.0:
                        insights_data.append({
                            "column_name": target_col,
                            "insight_type": "class_imbalance",
                            "severity": "critical" if ratio >= 10.0 else "high",
                            "message": f"Target column '{target_col}' shows significant class imbalance (ratio {round(ratio, 1)}:1).",
                            "suggested_action": "Use class-weighted loss, SMOTE oversampling, or evaluate using PR-AUC / balanced accuracy."
                        })

        # Sort insights by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        insights_data.sort(key=lambda x: severity_order.get(x["severity"], 4))

        # Clear existing insights for this dataset
        db.query(Insight).filter(Insight.dataset_id == dataset_id).delete()

        # Save to DB
        created_records = []
        for item in insights_data:
            rec = Insight(
                dataset_id=dataset_id,
                column_name=item.get("column_name"),
                insight_type=item["insight_type"],
                severity=item["severity"],
                message=item["message"],
                suggested_action=item.get("suggested_action")
            )
            db.add(rec)
            created_records.append(rec)

        db.commit()

        return [
            {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "column_name": r.column_name,
                "insight_type": r.insight_type,
                "severity": r.severity,
                "message": r.message,
                "suggested_action": r.suggested_action,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in created_records
        ]

    @staticmethod
    def get_insights(dataset_id: str, db: Session) -> List[Dict[str, Any]]:
        """Retrieve stored insights for a dataset."""
        records = db.query(Insight).filter(Insight.dataset_id == dataset_id).all()
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_records = sorted(records, key=lambda x: severity_order.get(x.severity, 4))
        return [
            {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "column_name": r.column_name,
                "insight_type": r.insight_type,
                "severity": r.severity,
                "message": r.message,
                "suggested_action": r.suggested_action,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in sorted_records
        ]
