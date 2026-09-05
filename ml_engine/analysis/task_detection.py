"""
Task Detection Engine — Determines target column and ML task type using deterministic heuristics.
Never claims certainty; uses confidence scores and explains reasoning.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class TaskDetectionEngine:
    """Detect target columns and classify ML task type from dataset structure."""

    # Column names that commonly indicate targets
    TARGET_NAME_SIGNALS = [
        "target", "label", "class", "outcome", "result",
        "churn", "default", "fraud", "spam", "survived",
        "diagnosis", "status", "y", "output",
        "price", "salary", "revenue", "cost", "amount",
        "score", "rating", "value",
    ]

    @classmethod
    def suggest_target(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Suggest potential target columns with confidence and reasoning.
        Returns a list of candidates ordered by confidence.
        """
        candidates = []
        columns = df.columns.tolist()
        n_rows = len(df)

        for col in columns:
            score = 0.0
            reasons = []
            series = df[col].dropna()

            if series.empty:
                continue

            col_lower = col.strip().lower().replace(" ", "_")

            # 1. Name signal
            for signal in cls.TARGET_NAME_SIGNALS:
                if signal in col_lower or col_lower == signal:
                    score += 0.30
                    reasons.append(f"Column name '{col}' matches common target pattern '{signal}'")
                    break

            # 2. Position signal (last column is often the target)
            if col == columns[-1]:
                score += 0.15
                reasons.append("Column is in the last position (commonly the target)")

            # 3. Cardinality signal (targets typically have low-medium cardinality)
            unique_ratio = series.nunique() / n_rows if n_rows > 0 else 0
            n_unique = series.nunique()

            if n_unique == 2:
                score += 0.20
                reasons.append(f"Binary column with exactly 2 unique values")
            elif 2 < n_unique <= 20:
                score += 0.10
                reasons.append(f"Low cardinality ({n_unique} unique values) — common for classification")
            elif pd.api.types.is_numeric_dtype(series) and n_unique > 20:
                score += 0.05
                reasons.append("Continuous numerical column — potential regression target")

            # 4. NOT an ID column (penalize)
            if unique_ratio > 0.95 and not pd.api.types.is_float_dtype(series):
                score -= 0.40
                reasons.append("Very high uniqueness suggests identifier, unlikely target")

            if any(kw in col_lower for kw in ["_id", "id_", "index", "key", "code", "number", "num"]):
                if col_lower not in ["account_number", "phone_number"]:
                    score -= 0.30
                    reasons.append("Column name suggests identifier")

            # 5. Date columns are not targets
            if pd.api.types.is_datetime64_any_dtype(series):
                score -= 0.50
                reasons.append("Datetime column — not a typical target")

            # Clamp
            score = max(0.0, min(1.0, score))

            if score > 0.1:
                candidates.append({
                    "column": col,
                    "confidence": round(score, 2),
                    "reasons": reasons,
                    "dtype": str(series.dtype),
                    "n_unique": int(n_unique),
                    "sample_values": [str(v) for v in series.unique()[:5]],
                })

        # Sort by confidence descending
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates

    @classmethod
    def detect_task(cls, df: pd.DataFrame, target: str) -> Dict[str, Any]:
        """
        Detect the ML task type for a given target column.
        Returns structured task information with confidence.
        """
        if target not in df.columns:
            return {
                "task": None,
                "target": target,
                "confidence": 0.0,
                "error": f"Column '{target}' not found in dataset.",
            }

        series = df[target].dropna()
        if series.empty:
            return {
                "task": None,
                "target": target,
                "confidence": 0.0,
                "error": f"Target column '{target}' contains only missing values.",
            }

        n_unique = series.nunique()
        is_numeric = pd.api.types.is_numeric_dtype(series)

        # Classification vs regression heuristics
        if n_unique == 1:
            return {
                "task": None,
                "target": target,
                "confidence": 0.0,
                "error": f"Target column '{target}' has only one unique value. Cannot train a model.",
            }

        if n_unique == 2:
            task = "binary_classification"
            confidence = 0.95
            class_distribution = series.value_counts().to_dict()
            return {
                "task": task,
                "target": target,
                "confidence": round(confidence, 2),
                "n_classes": 2,
                "class_distribution": {str(k): int(v) for k, v in class_distribution.items()},
                "recommendation": "Binary classification detected. Consider F1 or ROC-AUC as primary metric.",
            }

        if not is_numeric:
            # Categorical with > 2 classes
            if n_unique <= 50:
                task = "multiclass_classification"
                confidence = 0.90
            else:
                task = "multiclass_classification"
                confidence = 0.60  # High cardinality — could be wrong
            class_distribution = series.value_counts().head(20).to_dict()
            return {
                "task": task,
                "target": target,
                "confidence": round(confidence, 2),
                "n_classes": int(n_unique),
                "class_distribution": {str(k): int(v) for k, v in class_distribution.items()},
                "recommendation": f"Multiclass classification with {n_unique} classes detected.",
            }

        # Numeric target
        if n_unique <= 20:
            # Low-cardinality integer — likely classification
            task = "multiclass_classification" if n_unique > 2 else "binary_classification"
            confidence = 0.80
            class_distribution = series.value_counts().to_dict()
            return {
                "task": task,
                "target": target,
                "confidence": round(confidence, 2),
                "n_classes": int(n_unique),
                "class_distribution": {str(k): int(v) for k, v in class_distribution.items()},
                "recommendation": f"Numeric target with {n_unique} unique values — detected as classification.",
            }
        else:
            # Continuous numerical
            task = "regression"
            confidence = 0.90
            return {
                "task": task,
                "target": target,
                "confidence": round(confidence, 2),
                "stats": {
                    "mean": round(float(series.mean()), 4),
                    "median": round(float(series.median()), 4),
                    "std": round(float(series.std()), 4),
                    "min": round(float(series.min()), 4),
                    "max": round(float(series.max()), 4),
                },
                "recommendation": "Regression detected. Consider RMSE or R² as primary metric.",
            }
