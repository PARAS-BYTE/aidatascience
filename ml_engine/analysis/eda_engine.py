"""
EDA Engine — Generates exploratory data analysis from real dataset computations.

Computes: numerical stats, categorical stats, distributions, correlations,
target analysis, and data quality observations. Never fabricates results.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class EDAEngine:
    """Performs deterministic EDA computations on pandas DataFrames."""

    @staticmethod
    def compute_numerical_stats(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calculate statistical summaries for all numerical columns."""
        stats = []
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in numerical_cols:
            series = df[col].dropna()
            if series.empty:
                continue
            stats.append({
                "column": col,
                "count": int(series.count()),
                "mean": round(float(series.mean()), 4),
                "median": round(float(series.median()), 4),
                "std": round(float(series.std()), 4),
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
                "q1": round(float(series.quantile(0.25)), 4),
                "q3": round(float(series.quantile(0.75)), 4),
                "skew": round(float(series.skew()), 4),
                "kurtosis": round(float(series.kurtosis()), 4),
                "unique": int(series.nunique()),
                "missing": int(df[col].isna().sum()),
                "missing_pct": round(float(df[col].isna().mean() * 100), 2),
            })
        return stats

    @staticmethod
    def compute_categorical_stats(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calculate summaries for categorical/object columns."""
        stats = []
        cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

        for col in cat_cols:
            series = df[col].dropna()
            if series.empty:
                continue
            value_counts = series.value_counts()
            top_n = min(10, len(value_counts))
            top_categories = [
                {"value": str(val), "count": int(cnt), "percentage": round(float(cnt / len(series) * 100), 2)}
                for val, cnt in value_counts.head(top_n).items()
            ]
            stats.append({
                "column": col,
                "count": int(series.count()),
                "unique": int(series.nunique()),
                "top_value": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                "top_frequency": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "top_categories": top_categories,
                "missing": int(df[col].isna().sum()),
                "missing_pct": round(float(df[col].isna().mean() * 100), 2),
            })
        return stats

    @staticmethod
    def compute_distributions(df: pd.DataFrame, max_bins: int = 30) -> Dict[str, Any]:
        """Compute distribution data for histograms and bar charts."""
        distributions = {}

        # Numerical histograms
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for col in numerical_cols:
            series = df[col].dropna()
            if series.empty or series.nunique() < 2:
                continue
            n_bins = min(max_bins, max(10, int(np.sqrt(len(series)))))
            counts, bin_edges = np.histogram(series, bins=n_bins)
            distributions[col] = {
                "type": "histogram",
                "bins": [round(float(e), 4) for e in bin_edges],
                "counts": [int(c) for c in counts],
            }

        # Categorical bar charts
        cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
        for col in cat_cols:
            series = df[col].dropna()
            if series.empty:
                continue
            value_counts = series.value_counts().head(20)
            distributions[col] = {
                "type": "bar",
                "labels": [str(v) for v in value_counts.index],
                "counts": [int(c) for c in value_counts.values],
            }

        return distributions

    @staticmethod
    def compute_correlation_matrix(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate Pearson correlation matrix for numerical columns."""
        numerical_df = df.select_dtypes(include=[np.number])
        if numerical_df.shape[1] < 2:
            return {"columns": [], "matrix": []}

        corr = numerical_df.corr(method="pearson")
        columns = corr.columns.tolist()
        matrix = []
        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                val = corr.iloc[i, j]
                matrix.append({
                    "x": col1,
                    "y": col2,
                    "value": round(float(val), 4) if not np.isnan(val) else 0.0,
                })

        return {"columns": columns, "matrix": matrix}

    @staticmethod
    def compute_target_distribution(df: pd.DataFrame, target: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Analyze distribution of the target column."""
        if target is None or target not in df.columns:
            return None

        series = df[target].dropna()
        if series.empty:
            return None

        is_numeric = pd.api.types.is_numeric_dtype(series)

        if is_numeric and series.nunique() > 20:
            # Regression target — histogram
            n_bins = min(30, max(10, int(np.sqrt(len(series)))))
            counts, bin_edges = np.histogram(series, bins=n_bins)
            return {
                "type": "histogram",
                "target": target,
                "bins": [round(float(e), 4) for e in bin_edges],
                "counts": [int(c) for c in counts],
                "mean": round(float(series.mean()), 4),
                "median": round(float(series.median()), 4),
                "std": round(float(series.std()), 4),
            }
        else:
            # Classification target — bar chart
            value_counts = series.value_counts()
            total = len(series)
            return {
                "type": "bar",
                "target": target,
                "labels": [str(v) for v in value_counts.index],
                "counts": [int(c) for c in value_counts.values],
                "percentages": [round(float(c / total * 100), 2) for c in value_counts.values],
                "is_imbalanced": bool(value_counts.min() / value_counts.max() < 0.3),
            }

    @staticmethod
    def generate_observations(
        df: pd.DataFrame,
        profile_data: Optional[Dict] = None,
        target: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate data quality observations from actual statistics.
        Each observation has: type (info/warning/critical), message, column (optional).
        """
        observations = []
        rows, cols = df.shape

        # Missing value observations
        for col in df.columns:
            missing_pct = df[col].isna().mean() * 100
            if missing_pct > 0:
                severity = "critical" if missing_pct > 20 else ("warning" if missing_pct > 5 else "info")
                observations.append({
                    "type": severity,
                    "category": "missing_values",
                    "column": col,
                    "message": f"'{col}' contains {missing_pct:.1f}% missing values ({int(df[col].isna().sum())} cells).",
                })

        # Duplicate observations
        n_dupes = df.duplicated().sum()
        if n_dupes > 0:
            dupe_pct = n_dupes / rows * 100
            observations.append({
                "type": "warning" if dupe_pct > 5 else "info",
                "category": "duplicates",
                "column": None,
                "message": f"Dataset contains {n_dupes} duplicate rows ({dupe_pct:.1f}%).",
            })

        # ID-like column observations
        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            unique_ratio = series.nunique() / len(series)
            col_lower = col.lower()
            if (unique_ratio > 0.95 and not pd.api.types.is_float_dtype(series)) or \
               any(kw in col_lower for kw in ["_id", "id_", "code", "number"]) and unique_ratio > 0.9:
                observations.append({
                    "type": "info",
                    "category": "potential_id",
                    "column": col,
                    "message": f"'{col}' appears to be an identifier-like column ({series.nunique()} unique values out of {len(series)}).",
                })

        # Constant or near-constant columns
        for col in df.columns:
            if df[col].nunique(dropna=True) <= 1:
                observations.append({
                    "type": "warning",
                    "category": "constant_column",
                    "column": col,
                    "message": f"'{col}' has only {df[col].nunique(dropna=True)} unique value(s) and may not be useful.",
                })

        # Target-specific observations
        if target and target in df.columns:
            target_series = df[target].dropna()
            if pd.api.types.is_numeric_dtype(target_series) and target_series.nunique() <= 20:
                value_counts = target_series.value_counts()
                if len(value_counts) >= 2:
                    imbalance_ratio = value_counts.min() / value_counts.max()
                    if imbalance_ratio < 0.3:
                        distribution_str = ", ".join(
                            [f"{round(v / len(target_series) * 100, 1)}% {k}" for k, v in value_counts.items()]
                        )
                        observations.append({
                            "type": "warning",
                            "category": "class_imbalance",
                            "column": target,
                            "message": f"Target '{target}' is imbalanced: {distribution_str}.",
                        })
            elif not pd.api.types.is_numeric_dtype(target_series):
                value_counts = target_series.value_counts()
                if len(value_counts) >= 2:
                    imbalance_ratio = value_counts.min() / value_counts.max()
                    if imbalance_ratio < 0.3:
                        distribution_str = ", ".join(
                            [f"{round(v / len(target_series) * 100, 1)}% {k}" for k, v in value_counts.items()]
                        )
                        observations.append({
                            "type": "warning",
                            "category": "class_imbalance",
                            "column": target,
                            "message": f"Target '{target}' is imbalanced: {distribution_str}.",
                        })

        # High cardinality observations
        for col in df.select_dtypes(include=["object", "category"]).columns:
            n_unique = df[col].nunique()
            if n_unique > 50:
                observations.append({
                    "type": "info",
                    "category": "high_cardinality",
                    "column": col,
                    "message": f"'{col}' has {n_unique} unique values — may need encoding or grouping.",
                })

        return observations

    @classmethod
    def run_full_eda(
        cls,
        df: pd.DataFrame,
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the complete EDA pipeline and return structured results."""
        return {
            "numerical_stats": cls.compute_numerical_stats(df),
            "categorical_stats": cls.compute_categorical_stats(df),
            "distributions": cls.compute_distributions(df),
            "correlation": cls.compute_correlation_matrix(df),
            "target_distribution": cls.compute_target_distribution(df, target),
            "observations": cls.generate_observations(df, target=target),
            "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        }
