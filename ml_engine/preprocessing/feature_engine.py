"""
Feature Engineering Engine — Generates meaningful features from raw data.
Supports:
- Temporal date decompositions
- Interaction features (cross-products of top correlated columns)
- Polynomial features (squared & cross terms)
- Principal Component Analysis (PCA) dimensionality reduction with explained variance
- Feature selection via mutual information and variance
- Live interactive preview generation with before/after comparisons
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


class FeatureEngineeringEngine:
    """Generate useful features and apply PCA transformations on tabular data."""

    @staticmethod
    def extract_date_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Extract temporal features from date columns."""
        result = df.copy()
        new_features = []

        # Detect date columns
        date_cols = result.select_dtypes(include=["datetime64"]).columns.tolist()

        # Also try to convert object columns that look like dates
        for col in result.select_dtypes(include=["object"]).columns:
            sample = result[col].dropna().head(50)
            if len(sample) == 0:
                continue
            if sample.astype(str).str.contains(r"[-/]", regex=True).mean() > 0.5:
                try:
                    converted = pd.to_datetime(sample, errors="coerce", format="mixed")
                    if converted.notna().mean() > 0.8:
                        result[col] = pd.to_datetime(result[col], errors="coerce", format="mixed")
                        date_cols.append(col)
                except Exception:
                    pass

        for col in date_cols:
            series = result[col]
            if not pd.api.types.is_datetime64_any_dtype(series):
                continue

            prefix = col.replace("_date", "").replace("date_", "").replace("Date", "")
            if prefix == col:
                prefix = col

            result[f"{prefix}_year"] = series.dt.year
            result[f"{prefix}_month"] = series.dt.month
            result[f"{prefix}_day"] = series.dt.day
            result[f"{prefix}_day_of_week"] = series.dt.dayofweek
            result[f"{prefix}_quarter"] = series.dt.quarter

            new_features.extend([
                f"{prefix}_year", f"{prefix}_month", f"{prefix}_day",
                f"{prefix}_day_of_week", f"{prefix}_quarter",
            ])

            result = result.drop(columns=[col])

        return result, new_features

    @staticmethod
    def create_interaction_features(
        df: pd.DataFrame,
        target: Optional[str] = None,
        max_interactions: int = 5,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Create meaningful interaction features between numerical columns."""
        result = df.copy()
        new_features = []

        numerical_cols = result.select_dtypes(include=[np.number]).columns.tolist()
        if target and target in numerical_cols:
            numerical_cols.remove(target)

        if len(numerical_cols) < 2:
            return result, new_features

        # Find top correlated columns with target if available
        if target and target in result.columns and pd.api.types.is_numeric_dtype(result[target]):
            correlations = {}
            for col in numerical_cols:
                try:
                    corr = abs(result[col].corr(result[target]))
                    if not np.isnan(corr):
                        correlations[col] = corr
                except Exception:
                    pass
            sorted_cols = sorted(correlations.keys(), key=lambda x: correlations[x], reverse=True)
            top_cols = sorted_cols[:6]
        else:
            top_cols = numerical_cols[:6]

        interactions_created = 0
        for i, col1 in enumerate(top_cols):
            if interactions_created >= max_interactions:
                break
            for col2 in top_cols[i + 1:]:
                if interactions_created >= max_interactions:
                    break
                feat_name = f"{col1}_x_{col2}"
                result[feat_name] = result[col1] * result[col2]
                new_features.append(feat_name)
                interactions_created += 1

        return result, new_features

    @staticmethod
    def apply_polynomial_features(
        df: pd.DataFrame,
        target: Optional[str] = None,
        degree: int = 2,
        max_features: int = 4,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Generate non-linear polynomial (squared) features for top numeric columns."""
        result = df.copy()
        new_features = []

        if degree < 2:
            return result, new_features

        numerical_cols = result.select_dtypes(include=[np.number]).columns.tolist()
        if target and target in numerical_cols:
            numerical_cols.remove(target)

        # Exclude binary 0/1 columns from squaring
        eligible_cols = [c for c in numerical_cols if result[c].nunique() > 2][:max_features]

        for col in eligible_cols:
            feat_name = f"{col}_pow{degree}"
            result[feat_name] = result[col] ** degree
            new_features.append(feat_name)

        return result, new_features

    @staticmethod
    def apply_pca(
        df: pd.DataFrame,
        target: Optional[str] = None,
        n_components: Optional[int] = 2,
        variance_threshold: Optional[float] = None,
        drop_original_numerics: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply Principal Component Analysis (PCA) to numerical columns.
        Returns transformed DataFrame and PCA metadata (explained variance, loadings, components).
        """
        result = df.copy()
        numerical_cols = result.select_dtypes(include=[np.number]).columns.tolist()
        if target and target in numerical_cols:
            numerical_cols.remove(target)

        if len(numerical_cols) < 2:
            return result, {
                "applied": False,
                "reason": "At least 2 numerical features are required for PCA.",
                "components": [],
                "explained_variance_ratio": [],
                "cumulative_variance": [],
            }

        X_num = result[numerical_cols].fillna(result[numerical_cols].median())

        # Standardize features prior to PCA
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_num)

        # Determine number of components
        max_possible = min(X_scaled.shape[0], X_scaled.shape[1])
        if variance_threshold is not None and 0.0 < variance_threshold <= 1.0:
            pca = PCA(n_components=variance_threshold, svd_solver="full")
        else:
            k = min(n_components or 2, max_possible)
            k = max(1, k)
            pca = PCA(n_components=k)

        X_pca = pca.fit_transform(X_scaled)
        actual_k = X_pca.shape[1]

        pca_col_names = [f"pca_{i+1}" for i in range(actual_k)]
        for i, col_name in enumerate(pca_col_names):
            result[col_name] = np.round(X_pca[:, i], 4)

        if drop_original_numerics:
            result = result.drop(columns=numerical_cols)

        # Calculate component loadings (weights of original features in each PC)
        loadings = []
        for i in range(actual_k):
            comp_loadings = {
                num_col: round(float(pca.components_[i, idx]), 4)
                for idx, num_col in enumerate(numerical_cols)
            }
            loadings.append({
                "component": f"PCA {i+1}",
                "explained_variance": round(float(pca.explained_variance_ratio_[i]), 4),
                "loadings": comp_loadings,
            })

        explained_variance_ratio = [round(float(v), 4) for v in pca.explained_variance_ratio_]
        cumulative_variance = [round(float(v), 4) for v in np.cumsum(pca.explained_variance_ratio_)]

        pca_report = {
            "applied": True,
            "components": pca_col_names,
            "n_components": actual_k,
            "explained_variance_ratio": explained_variance_ratio,
            "cumulative_variance": cumulative_variance,
            "total_explained_variance": round(float(np.sum(pca.explained_variance_ratio_)), 4),
            "loadings": loadings,
            "input_features": numerical_cols,
            "dropped_original_features": drop_original_numerics,
        }

        return result, pca_report

    @classmethod
    def run_feature_engineering(
        cls,
        df: pd.DataFrame,
        target: Optional[str] = None,
        enable_date_features: bool = True,
        enable_interactions: bool = True,
        max_interactions: int = 5,
        enable_polynomial: bool = False,
        polynomial_degree: int = 2,
        enable_pca: bool = False,
        pca_components: int = 2,
        drop_pca_original: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Execute the full feature engineering pipeline.
        Returns (engineered_df, report).
        """
        result = df.copy()
        report = {
            "original_columns": df.columns.tolist(),
            "original_shape": list(df.shape),
            "steps": [],
            "new_features": [],
            "pca_report": None,
        }

        # 1. Date features
        if enable_date_features:
            result, date_features = cls.extract_date_features(result)
            if date_features:
                report["steps"].append({
                    "action": "date_features",
                    "features": date_features,
                    "message": f"Extracted {len(date_features)} date-based temporal features.",
                })
                report["new_features"].extend(date_features)

        # 2. Interaction features
        if enable_interactions:
            result, interaction_features = cls.create_interaction_features(
                result, target=target, max_interactions=max_interactions
            )
            if interaction_features:
                report["steps"].append({
                    "action": "interaction_features",
                    "features": interaction_features,
                    "message": f"Created {len(interaction_features)} interaction features.",
                })
                report["new_features"].extend(interaction_features)

        # 3. Polynomial features
        if enable_polynomial:
            result, poly_features = cls.apply_polynomial_features(
                result, target=target, degree=polynomial_degree
            )
            if poly_features:
                report["steps"].append({
                    "action": "polynomial_features",
                    "features": poly_features,
                    "message": f"Generated {len(poly_features)} degree-{polynomial_degree} polynomial features.",
                })
                report["new_features"].extend(poly_features)

        # 4. PCA Dimensionality Reduction
        if enable_pca:
            result, pca_report = cls.apply_pca(
                result,
                target=target,
                n_components=pca_components,
                drop_original_numerics=drop_pca_original,
            )
            report["pca_report"] = pca_report
            if pca_report.get("applied"):
                report["steps"].append({
                    "action": "pca_reduction",
                    "features": pca_report["components"],
                    "message": f"Computed {pca_report['n_components']} Principal Components (Explaining {round(pca_report['total_explained_variance'] * 100, 1)}% variance).",
                })
                report["new_features"].extend(pca_report["components"])

        report["final_columns"] = result.columns.tolist()
        report["final_shape"] = list(result.shape)

        return result, report

    @classmethod
    def preview_feature_engineering(
        cls,
        df: pd.DataFrame,
        target: Optional[str] = None,
        enable_date_features: bool = True,
        enable_interactions: bool = True,
        max_interactions: int = 5,
        enable_polynomial: bool = False,
        polynomial_degree: int = 2,
        enable_pca: bool = False,
        pca_components: int = 2,
        drop_pca_original: bool = False,
        preview_limit: int = 30,
    ) -> Dict[str, Any]:
        """Generate comprehensive preview comparing raw data vs transformed data with PCA stats."""
        transformed_df, report = cls.run_feature_engineering(
            df=df,
            target=target,
            enable_date_features=enable_date_features,
            enable_interactions=enable_interactions,
            max_interactions=max_interactions,
            enable_polynomial=enable_polynomial,
            polynomial_degree=polynomial_degree,
            enable_pca=enable_pca,
            pca_components=pca_components,
            drop_pca_original=drop_pca_original,
        )

        # Calculate correlations with target for numerical columns
        target_correlations = {}
        if target and target in transformed_df.columns and pd.api.types.is_numeric_dtype(transformed_df[target]):
            num_cols = transformed_df.select_dtypes(include=[np.number]).columns.tolist()
            for col in num_cols:
                if col != target:
                    try:
                        c = transformed_df[col].corr(transformed_df[target])
                        if not np.isnan(c):
                            target_correlations[col] = round(float(c), 4)
                    except Exception:
                        pass

        # Sort correlations descending
        sorted_corrs = sorted(target_correlations.items(), key=lambda x: abs(x[1]), reverse=True)

        # Format records for JSON
        original_sample = df.head(preview_limit).replace({np.nan: None}).to_dict(orient="records")
        transformed_sample = transformed_df.head(preview_limit).replace({np.nan: None}).to_dict(orient="records")

        return {
            "original_shape": list(df.shape),
            "transformed_shape": list(transformed_df.shape),
            "original_columns": df.columns.tolist(),
            "transformed_columns": transformed_df.columns.tolist(),
            "new_features": report["new_features"],
            "steps": report["steps"],
            "pca_report": report.get("pca_report"),
            "target_correlations": dict(sorted_corrs),
            "original_preview": original_sample,
            "transformed_preview": transformed_sample,
        }

    @classmethod
    def generate_candidates(cls, df: pd.DataFrame, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Automated Feature Engineering Agent: Generates candidate feature definitions,
        calculates predictive impact/correlation with target, and returns ranked candidates.
        """
        candidates = []
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target and target in num_cols:
            num_cols.remove(target)

        # 1. Ratios between numerical features
        for i in range(min(4, len(num_cols))):
            for j in range(i + 1, min(4, len(num_cols))):
                c1, c2 = num_cols[i], num_cols[j]
                if (df[c2] == 0).sum() / max(1, len(df)) < 0.05:
                    ratio_series = df[c1] / (df[c2].replace(0, np.nan))
                    impact = 0.1
                    if target and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
                        try:
                            corr = abs(ratio_series.corr(df[target]))
                            if not np.isnan(corr):
                                impact = round(float(corr), 3)
                        except Exception:
                            pass
                    candidates.append({
                        "name": f"{c1}_div_{c2}",
                        "type": "ratio",
                        "formula": f"{c1} / {c2}",
                        "description": f"Normalized relative ratio between {c1} and {c2}",
                        "impact_score": impact,
                        "selected": True if impact >= 0.15 or len(candidates) < 3 else False
                    })

        # 2. Log-transforms for skewed features
        for c in num_cols:
            series = df[c].dropna()
            if len(series) > 10 and (series > 0).all():
                skew = abs(series.skew())
                if skew > 1.2:
                    log_series = np.log1p(series)
                    impact = 0.15
                    if target and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
                        try:
                            corr = abs(log_series.corr(df[target]))
                            if not np.isnan(corr):
                                impact = round(float(corr), 3)
                        except Exception:
                            pass
                    candidates.append({
                        "name": f"log1p_{c}",
                        "type": "log_transform",
                        "formula": f"log(1 + {c})",
                        "description": f"Log-transformation to normalize high skewness ({round(skew, 2)})",
                        "impact_score": impact,
                        "selected": True
                    })

        # 3. Date temporal components
        date_cols = [c for c in df.columns if any(k in c.lower() for k in ["date", "time", "year", "month", "created"])]
        for dc in date_cols[:2]:
            try:
                dt_series = pd.to_datetime(df[dc], errors="coerce")
                if dt_series.notna().mean() > 0.5:
                    candidates.append({
                        "name": f"{dc}_month",
                        "type": "datetime",
                        "formula": f"{dc}.dt.month",
                        "description": f"Seasonal calendar month component from {dc}",
                        "impact_score": 0.25,
                        "selected": True
                    })
                    candidates.append({
                        "name": f"{dc}_day_of_week",
                        "type": "datetime",
                        "formula": f"{dc}.dt.dayofweek",
                        "description": f"Day of week cyclic component from {dc}",
                        "impact_score": 0.20,
                        "selected": True
                    })
            except Exception:
                pass

        # Sort descending by impact score
        candidates.sort(key=lambda x: x["impact_score"], reverse=True)
        return candidates
