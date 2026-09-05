"""
Data Cleaning / Preprocessing Engine — Builds sklearn-compatible pipelines.
Prevents data leakage by fitting only on training data.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, List, Optional, Tuple
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.model_selection import train_test_split


class CleaningEngine:
    """Deterministic data cleaning and preprocessing pipeline builder."""

    @staticmethod
    def detect_issues(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect data quality issues without modifying the dataset."""
        rows, cols = df.shape
        total_cells = rows * cols

        # Missing values
        missing_per_col = df.isna().sum()
        total_missing = int(missing_per_col.sum())
        missing_pct = round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0.0

        missing_details = []
        for col in df.columns:
            mc = int(missing_per_col[col])
            if mc > 0:
                missing_details.append({
                    "column": col,
                    "count": mc,
                    "percentage": round(mc / rows * 100, 2),
                })

        # Duplicates
        n_duplicates = int(df.duplicated().sum())
        dup_pct = round(n_duplicates / rows * 100, 2) if rows > 0 else 0.0

        # Constant columns
        constant_cols = [col for col in df.columns if df[col].nunique(dropna=True) <= 1]

        # Potential ID columns
        potential_ids = []
        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            unique_ratio = series.nunique() / len(series)
            col_lower = col.lower()
            is_id_name = any(kw in col_lower for kw in ["_id", "id_", "index", "guid", "uuid"]) or col_lower == "id"
            is_object_str = pd.api.types.is_object_dtype(series) or str(series.dtype) in ("string", "object")
            if is_id_name or (is_object_str and unique_ratio > 0.95 and len(series) >= 20):
                potential_ids.append(col)

        # Outliers (IQR for numerical columns)
        outlier_cols = []
        for col in df.select_dtypes(include=[np.number]).columns:
            series = df[col].dropna()
            if len(series) < 10:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            n_outliers = int(((series < lower) | (series > upper)).sum())
            if n_outliers > 0:
                outlier_cols.append({
                    "column": col,
                    "count": n_outliers,
                    "percentage": round(n_outliers / len(series) * 100, 2),
                    "lower_bound": round(float(lower), 4),
                    "upper_bound": round(float(upper), 4),
                })

        return {
            "total_missing": total_missing,
            "missing_percentage": missing_pct,
            "missing_details": missing_details,
            "duplicates": n_duplicates,
            "duplicate_percentage": dup_pct,
            "constant_columns": constant_cols,
            "potential_ids": potential_ids,
            "outlier_columns": outlier_cols,
            "rows": rows,
            "columns": cols,
        }

    @staticmethod
    def clean_dataset(
        df: pd.DataFrame,
        target: str,
        drop_ids: bool = True,
        drop_constants: bool = True,
        remove_duplicates: bool = True,
        handle_missing: str = "auto",  # "auto", "drop", "impute"
        detected_ids: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Clean the dataset and return (cleaned_df, cleaning_report).
        Does NOT fit any transformers — that happens in build_preprocessing_pipeline.
        """
        report = {"steps": [], "rows_before": len(df), "cols_before": len(df.columns)}
        cleaned = df.copy()

        # 1. Remove duplicates
        if remove_duplicates:
            n_before = len(cleaned)
            cleaned = cleaned.drop_duplicates()
            n_removed = n_before - len(cleaned)
            if n_removed > 0:
                report["steps"].append({
                    "action": "remove_duplicates",
                    "removed": n_removed,
                    "message": f"Removed {n_removed} duplicate rows.",
                })

        # 2. Drop constant columns
        if drop_constants:
            const_cols = [c for c in cleaned.columns if c != target and cleaned[c].nunique(dropna=True) <= 1]
            if const_cols:
                cleaned = cleaned.drop(columns=const_cols)
                report["steps"].append({
                    "action": "drop_constant_columns",
                    "columns": const_cols,
                    "message": f"Dropped {len(const_cols)} constant column(s): {', '.join(const_cols)}.",
                })

        # 3. Drop ID columns
        if drop_ids and detected_ids:
            id_cols = [c for c in detected_ids if c in cleaned.columns and c != target]
            if id_cols:
                cleaned = cleaned.drop(columns=id_cols)
                report["steps"].append({
                    "action": "drop_id_columns",
                    "columns": id_cols,
                    "message": f"Dropped {len(id_cols)} identifier column(s): {', '.join(id_cols)}.",
                })

        # 4. Handle missing values
        if handle_missing == "drop":
            n_before = len(cleaned)
            cleaned = cleaned.dropna()
            n_removed = n_before - len(cleaned)
            report["steps"].append({
                "action": "drop_missing_rows",
                "removed": n_removed,
                "message": f"Dropped {n_removed} rows with missing values.",
            })
        elif handle_missing in ("auto", "impute"):
            # Drop columns with >50% missing
            high_missing = [c for c in cleaned.columns if c != target and cleaned[c].isna().mean() > 0.5]
            if high_missing:
                cleaned = cleaned.drop(columns=high_missing)
                report["steps"].append({
                    "action": "drop_high_missing_columns",
                    "columns": high_missing,
                    "message": f"Dropped {len(high_missing)} columns with >50% missing: {', '.join(high_missing)}.",
                })
            # Drop rows where target is missing
            n_target_missing = cleaned[target].isna().sum()
            if n_target_missing > 0:
                cleaned = cleaned.dropna(subset=[target])
                report["steps"].append({
                    "action": "drop_target_missing",
                    "removed": int(n_target_missing),
                    "message": f"Dropped {n_target_missing} rows where target '{target}' is missing.",
                })
            # Note: remaining imputation happens in the sklearn pipeline

        report["rows_after"] = len(cleaned)
        report["cols_after"] = len(cleaned.columns)
        report["remaining_columns"] = cleaned.columns.tolist()

        return cleaned, report

    @staticmethod
    def build_preprocessing_pipeline(
        df: pd.DataFrame,
        target: str,
        task_type: Optional[str] = None,
    ) -> Tuple[ColumnTransformer, Optional[LabelEncoder], List[str], List[str]]:
        """
        Build a sklearn ColumnTransformer for feature preprocessing.
        Returns (preprocessor, label_encoder, numerical_cols, categorical_cols).
        The preprocessor must be fit on TRAINING data only.
        """
        feature_cols = [c for c in df.columns if c != target]
        numerical_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df[feature_cols].select_dtypes(include=["object", "category", "bool"]).columns.tolist()

        # Numerical pipeline: impute median → scale
        numerical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])

        # Categorical pipeline: impute most frequent → one-hot encode
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])

        transformers = []
        if numerical_cols:
            transformers.append(("num", numerical_pipeline, numerical_cols))
        if categorical_cols:
            transformers.append(("cat", categorical_pipeline, categorical_cols))

        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder="drop",
        )

        # Label encoder for classification targets (never for regression)
        label_encoder = None
        is_regression = task_type and "regression" in task_type.lower()
        if not is_regression:
            if not pd.api.types.is_numeric_dtype(df[target]) or (task_type and "classification" in task_type.lower()):
                label_encoder = LabelEncoder()
            elif df[target].nunique() <= 20 and pd.api.types.is_integer_dtype(df[target]):
                label_encoder = LabelEncoder()

        return preprocessor, label_encoder, numerical_cols, categorical_cols

    @staticmethod
    def prepare_train_test(
        df: pd.DataFrame,
        target: str,
        test_size: float = 0.2,
        random_seed: int = 42,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Split dataset into train/test ensuring no leakage."""
        X = df.drop(columns=[target])
        y = df[target]

        stratify_col = None
        if not pd.api.types.is_float_dtype(y) and y.nunique() <= 50:
            val_counts = y.value_counts()
            if len(val_counts) > 1 and int(val_counts.min()) >= 2:
                stratify_col = y

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=random_seed,
                stratify=stratify_col,
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=random_seed,
                stratify=None,
            )

        return X_train, X_test, y_train, y_test

    @staticmethod
    def save_preprocessing_artifacts(
        preprocessor: ColumnTransformer,
        label_encoder: Optional[LabelEncoder],
        numerical_cols: List[str],
        categorical_cols: List[str],
        save_dir: str,
        prefix: str = "preprocessing",
    ) -> Dict[str, str]:
        """Save fitted preprocessing artifacts to disk."""
        os.makedirs(save_dir, exist_ok=True)

        preprocessor_path = os.path.join(save_dir, f"{prefix}_pipeline.joblib")
        joblib.dump(preprocessor, preprocessor_path)

        meta = {
            "numerical_columns": numerical_cols,
            "categorical_columns": categorical_cols,
            "has_label_encoder": label_encoder is not None,
        }

        if label_encoder is not None:
            encoder_path = os.path.join(save_dir, f"{prefix}_label_encoder.joblib")
            joblib.dump(label_encoder, encoder_path)
            meta["label_encoder_path"] = encoder_path

        meta_path = os.path.join(save_dir, f"{prefix}_meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return {
            "preprocessor_path": preprocessor_path,
            "meta_path": meta_path,
        }

    @staticmethod
    def load_preprocessing_artifacts(
        save_dir: str,
        prefix: str = "preprocessing",
    ) -> Tuple[ColumnTransformer, Optional[LabelEncoder], Dict]:
        """Load fitted preprocessing artifacts from disk."""
        preprocessor_path = os.path.join(save_dir, f"{prefix}_pipeline.joblib")
        meta_path = os.path.join(save_dir, f"{prefix}_meta.json")

        preprocessor = joblib.load(preprocessor_path)

        with open(meta_path, "r") as f:
            meta = json.load(f)

        label_encoder = None
        if meta.get("has_label_encoder"):
            encoder_path = os.path.join(save_dir, f"{prefix}_label_encoder.joblib")
            label_encoder = joblib.load(encoder_path)

        return preprocessor, label_encoder, meta
