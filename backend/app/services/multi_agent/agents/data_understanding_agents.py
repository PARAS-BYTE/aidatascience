"""
Data Understanding Agents — Execute concurrently upon dataset upload or initial analysis.
1. ProfilingAgent: Schema, row/col counts, memory footprint, missingness overview
2. DataQualityAgent: Inconsistencies, duplicates, constant columns, mixed types, ID-like features
3. StatisticsAgent: Descriptive metrics, skewness, kurtosis, distributions, correlation matrix
4. RelationshipAgent: Cross-column and multi-file join keys, foreign-key relationships, cardinality
5. SemanticAgent: Business meaning of columns (currency, timestamp, user_id, geo, category, metric)
"""
import re
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.multi_agent.blackboard import SharedBlackboard


class ProfilingAgent:
    """Computes schema, types, shape, memory, and sample records."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        rows, cols = df.shape
        mem_bytes = int(df.memory_usage(deep=True).sum())
        mem_mb = round(mem_bytes / (1024 * 1024), 2)

        column_profiles = []
        for col in df.columns:
            series = df[col]
            dtype_str = str(series.dtype)
            null_count = int(series.isnull().sum())
            null_pct = round((null_count / rows) * 100, 2) if rows > 0 else 0
            n_unique = int(series.nunique(dropna=True))

            column_profiles.append({
                "name": str(col),
                "dtype": dtype_str,
                "null_count": null_count,
                "null_percentage": null_pct,
                "unique_count": n_unique,
                "cardinality_ratio": round(n_unique / rows, 4) if rows > 0 else 0,
                "sample_values": [str(v) for v in series.dropna().iloc[:3].tolist()],
            })

        profile_data = {
            "row_count": rows,
            "column_count": cols,
            "memory_mb": mem_mb,
            "total_null_cells": int(df.isnull().sum().sum()),
            "total_cells": rows * cols,
            "overall_completeness_pct": round((1.0 - (df.isnull().sum().sum() / (rows * cols or 1))) * 100, 2),
            "columns": column_profiles,
            "sample_head": df.head(5).fillna("").to_dict(orient="records"),
        }

        blackboard.set("profile", profile_data, agent_name="ProfilingAgent")
        return profile_data


class DataQualityAgent:
    """Audits data quality issues, duplicates, constants, ID columns, and anomalies."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        rows, cols = df.shape
        issues: List[Dict[str, Any]] = []
        quality_score = 100.0

        # 1. Duplicates
        duplicate_rows = int(df.duplicated().sum())
        if duplicate_rows > 0:
            dup_pct = round((duplicate_rows / rows) * 100, 2)
            issues.append({
                "type": "duplicate_rows",
                "severity": "high" if dup_pct > 10 else "medium",
                "message": f"Found {duplicate_rows} duplicate rows ({dup_pct}% of dataset).",
                "affected_columns": [],
                "deduction": min(20.0, dup_pct * 2),
            })
            quality_score -= min(20.0, dup_pct * 2)

        # 2. Missing values per column
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                null_pct = round((null_count / rows) * 100, 2)
                severity = "high" if null_pct > 40 else ("medium" if null_pct > 10 else "low")
                issues.append({
                    "type": "missing_values",
                    "severity": severity,
                    "column": str(col),
                    "message": f"Column '{col}' has {null_count} missing values ({null_pct}%).",
                    "affected_columns": [str(col)],
                    "deduction": 5.0 if severity == "high" else 2.0,
                })
                quality_score -= (5.0 if severity == "high" else 2.0)

        # 3. Constant or single-value columns
        for col in df.columns:
            if df[col].nunique(dropna=False) <= 1:
                issues.append({
                    "type": "constant_column",
                    "severity": "medium",
                    "column": str(col),
                    "message": f"Column '{col}' contains only 1 unique value (zero variance).",
                    "affected_columns": [str(col)],
                    "deduction": 4.0,
                })
                quality_score -= 4.0

        # 4. High cardinality ID-like columns
        id_like_cols = []
        for col in df.columns:
            col_lower = str(col).lower()
            if df[col].nunique() == rows and rows > 20:
                if any(k in col_lower for k in ["id", "uuid", "key", "guid", "index", "code"]):
                    id_like_cols.append(str(col))

        if id_like_cols:
            issues.append({
                "type": "id_columns",
                "severity": "info",
                "message": f"Potential primary key/ID columns identified: {', '.join(id_like_cols)}.",
                "affected_columns": id_like_cols,
                "deduction": 0.0,
            })

        quality_score = max(0.0, min(100.0, round(quality_score, 1)))

        quality_data = {
            "quality_score": quality_score,
            "status": "Excellent" if quality_score >= 90 else ("Good" if quality_score >= 75 else "Needs Cleaning"),
            "duplicate_count": duplicate_rows,
            "issue_count": len(issues),
            "issues": issues,
            "clean_readiness": quality_score >= 70,
        }

        blackboard.set("quality", quality_data, agent_name="DataQualityAgent")
        return quality_data


class StatisticsAgent:
    """Computes descriptive stats, skewness, kurtosis, distributions, and correlation matrices."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        numeric_df = df.select_dtypes(include=[np.number])
        numeric_cols = list(numeric_df.columns)

        stats_summary: Dict[str, Any] = {}
        for col in numeric_cols:
            s = numeric_df[col].dropna()
            if len(s) == 0:
                continue
            mean_val = float(s.mean())
            std_val = float(s.std()) if len(s) > 1 else 0.0
            skew_val = float(s.skew()) if len(s) > 2 else 0.0
            kurt_val = float(s.kurt()) if len(s) > 3 else 0.0

            stats_summary[str(col)] = {
                "count": int(len(s)),
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "min": round(float(s.min()), 4),
                "q25": round(float(s.quantile(0.25)), 4),
                "median": round(float(s.median()), 4),
                "q75": round(float(s.quantile(0.75)), 4),
                "max": round(float(s.max()), 4),
                "skewness": round(skew_val, 3),
                "kurtosis": round(kurt_val, 3),
                "distribution_shape": (
                    "Right-Skewed" if skew_val > 1.0 else
                    ("Left-Skewed" if skew_val < -1.0 else "Symmetric / Normal")
                ),
            }

        # Correlation matrix
        corr_matrix: Dict[str, Dict[str, float]] = {}
        high_correlations: List[Dict[str, Any]] = []
        if len(numeric_cols) >= 2:
            corr_df = numeric_df.corr().fillna(0.0)
            for c1 in numeric_cols:
                corr_matrix[str(c1)] = {}
                for c2 in numeric_cols:
                    val = round(float(corr_df.loc[c1, c2]), 3)
                    corr_matrix[str(c1)][str(c2)] = val
                    if c1 < c2 and abs(val) >= 0.65:
                        high_correlations.append({
                            "feature_a": str(c1),
                            "feature_b": str(c2),
                            "correlation": val,
                            "relationship": "Strong Positive" if val > 0 else "Strong Negative",
                        })

        stats_data = {
            "numeric_columns_count": len(numeric_cols),
            "categorical_columns_count": len(df.columns) - len(numeric_cols),
            "summary": stats_summary,
            "correlation_matrix": corr_matrix,
            "high_correlations": sorted(high_correlations, key=lambda x: abs(x["correlation"]), reverse=True)[:10],
        }

        blackboard.set("statistics", stats_data, agent_name="StatisticsAgent")
        return stats_data


class RelationshipAgent:
    """Discovers foreign-key candidates, join keys, and multi-file relationships."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        rows = len(df)
        potential_keys = []
        cardinality_map = {}

        for col in df.columns:
            n_unique = df[col].nunique(dropna=True)
            ratio = n_unique / rows if rows > 0 else 0
            col_name = str(col).lower()

            if ratio >= 0.95:
                potential_keys.append({
                    "column": str(col),
                    "type": "Candidate Primary Key",
                    "uniqueness_pct": round(ratio * 100, 2),
                })
            elif 0.05 < ratio < 0.95 and any(k in col_name for k in ["id", "code", "fk", "parent", "category", "dept"]):
                potential_keys.append({
                    "column": str(col),
                    "type": "Candidate Foreign Key",
                    "distinct_values": n_unique,
                })

            cardinality_map[str(col)] = "1:1" if ratio >= 0.98 else ("1:Many" if n_unique < rows * 0.5 else "Many:Many")

        rel_data = {
            "candidate_keys": potential_keys,
            "cardinality": cardinality_map,
            "multi_table_ready": len(potential_keys) > 0,
        }

        blackboard.set("relationships", rel_data, agent_name="RelationshipAgent")
        return rel_data


class SemanticAgent:
    """Infers business and contextual meaning of columns beyond raw dtypes."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        semantics: Dict[str, Dict[str, Any]] = {}
        target_candidates: List[str] = []
        date_columns: List[str] = []
        metric_columns: List[str] = []
        dimension_columns: List[str] = []

        for col in df.columns:
            col_name = str(col)
            col_lower = col_name.lower()
            series = df[col]
            dtype = str(series.dtype)

            # Check datetime
            if "datetime" in dtype or any(k in col_lower for k in ["date", "time", "timestamp", "year", "month", "day", "created_at"]):
                role = "temporal"
                date_columns.append(col_name)
            # Check currency/financial
            elif any(k in col_lower for k in ["price", "revenue", "sales", "cost", "profit", "amount", "salary", "balance", "fee", "margin", "income", "spend"]):
                role = "financial_metric"
                metric_columns.append(col_name)
            # Check identifiers
            elif any(k in col_lower for k in ["id", "uuid", "guid", "code", "ssn", "isbn", "email", "phone"]):
                role = "identifier"
            # Check geographic
            elif any(k in col_lower for k in ["country", "state", "city", "region", "zip", "postal", "lat", "lon", "address"]):
                role = "geographic"
                dimension_columns.append(col_name)
            # Check target/outcome
            elif any(k in col_lower for k in ["target", "churn", "label", "outcome", "converted", "default", "fraud", "attrition", "status", "class"]):
                role = "target_outcome"
                target_candidates.append(col_name)
            # Check numeric metric
            elif np.issubdtype(series.dtype, np.number):
                role = "numeric_metric"
                metric_columns.append(col_name)
            else:
                role = "categorical_dimension"
                dimension_columns.append(col_name)

            semantics[col_name] = {
                "semantic_role": role,
                "inferred_type": (
                    "Currency / Amount" if role == "financial_metric" else
                    ("Date / Timestamp" if role == "temporal" else
                    ("Entity Identifier" if role == "identifier" else
                    ("Geographic Entity" if role == "geographic" else
                    ("Business Target" if role == "target_outcome" else
                    ("Metric Measure" if role == "numeric_metric" else "Categorical Dimension")))))
                ),
                "is_dimension": role in ["categorical_dimension", "geographic", "temporal"],
                "is_metric": role in ["financial_metric", "numeric_metric"],
                "is_target_candidate": role == "target_outcome" or (col_name in target_candidates),
            }

        semantic_data = {
            "column_semantics": semantics,
            "metric_columns": metric_columns,
            "dimension_columns": dimension_columns,
            "date_columns": date_columns,
            "target_candidates": target_candidates or (metric_columns[:1] if metric_columns else []),
        }

        blackboard.set("semantics", semantic_data, agent_name="SemanticAgent")
        return semantic_data
