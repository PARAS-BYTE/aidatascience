"""
Reversible Cleaning Pipeline Service — Allows adding, toggling, reordering,
replaying, and inspecting diffs of data cleaning operations.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Dataset, PipelineStep
from app.services.profiler import DatasetProfiler
from app.core.config import settings

logger = logging.getLogger(__name__)


class PipelineService:
    @staticmethod
    def apply_operation(df: pd.DataFrame, operation: str, params: Dict[str, Any]) -> pd.DataFrame:
        """Apply a single atomic cleaning operation to a DataFrame."""
        df = df.copy()

        if operation == "drop_duplicates":
            subset = params.get("subset")
            df = df.drop_duplicates(subset=subset if subset else None)

        elif operation == "drop_column":
            col = params.get("column")
            if col and col in df.columns:
                df = df.drop(columns=[col])

        elif operation == "impute_missing":
            col = params.get("column")
            strategy = params.get("strategy", "median")
            fill_value = params.get("fill_value")

            cols_to_impute = [col] if col and col in df.columns else df.columns.tolist()
            for c in cols_to_impute:
                if df[c].isna().sum() == 0:
                    continue
                if strategy == "median" and pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].median())
                elif strategy == "mean" and pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].mean())
                elif strategy == "mode":
                    mode_val = df[c].mode()
                    if not mode_val.empty:
                        df[c] = df[c].fillna(mode_val.iloc[0])
                elif strategy == "constant" and fill_value is not None:
                    df[c] = df[c].fillna(fill_value)
                elif strategy == "drop_rows":
                    df = df.dropna(subset=[c])

        elif operation == "clip_outliers":
            col = params.get("column")
            iqr_factor = float(params.get("iqr_factor", 1.5))
            cols_to_clip = [col] if col and col in df.columns else df.select_dtypes(include=[np.number]).columns.tolist()

            for c in cols_to_clip:
                if pd.api.types.is_numeric_dtype(df[c]):
                    q1 = df[c].quantile(0.25)
                    q3 = df[c].quantile(0.75)
                    iqr = q3 - q1
                    if iqr > 0:
                        lower = q1 - iqr_factor * iqr
                        upper = q3 + iqr_factor * iqr
                        df[c] = df[c].clip(lower=lower, upper=upper)

        elif operation == "rename_column":
            old_name = params.get("old_name")
            new_name = params.get("new_name")
            if old_name and new_name and old_name in df.columns:
                df = df.rename(columns={old_name: new_name})

        elif operation == "scale_standard":
            col = params.get("column")
            cols = [col] if col and col in df.columns else df.select_dtypes(include=[np.number]).columns.tolist()
            for c in cols:
                std = df[c].std()
                if std and std > 0:
                    df[c] = (df[c] - df[c].mean()) / std

        elif operation == "one_hot_encode":
            col = params.get("column")
            if col and col in df.columns:
                df = pd.get_dummies(df, columns=[col], drop_first=True, dtype=float)

        return df

    @classmethod
    def replay_pipeline(cls, dataset_id: str, db: Session) -> Dict[str, Any]:
        """Load raw dataset file, apply all active pipeline steps, and save to cleaned file."""
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        df = DatasetProfiler.load_dataset(dataset.file_path)
        initial_rows, initial_cols = df.shape

        steps = db.query(PipelineStep).filter(
            PipelineStep.dataset_id == dataset_id,
            PipelineStep.is_active == True
        ).order_by(PipelineStep.step_order.asc()).all()

        executed_steps = []
        for step in steps:
            params = json.loads(step.params) if step.params else {}
            try:
                df = cls.apply_operation(df, step.operation, params)
                executed_steps.append({"step_id": step.id, "operation": step.operation, "status": "success"})
            except Exception as e:
                logger.error(f"Error applying step {step.id} ({step.operation}): {e}")
                executed_steps.append({"step_id": step.id, "operation": step.operation, "status": "failed", "error": str(e)})

        # Save to cleaned file path
        cleaned_path = dataset.cleaned_file_path
        if not cleaned_path:
            cleaned_path = os.path.join(settings.PROCESSED_DIR, f"cleaned_{dataset.stored_filename}")
            dataset.cleaned_file_path = cleaned_path

        df.to_csv(cleaned_path, index=False)
        db.commit()

        final_rows, final_cols = df.shape
        return {
            "dataset_id": dataset_id,
            "initial_shape": [initial_rows, initial_cols],
            "final_shape": [final_rows, final_cols],
            "active_steps_applied": len(executed_steps),
            "steps": executed_steps,
            "cleaned_file_path": cleaned_path
        }

    @classmethod
    def get_step_diff(cls, dataset_id: str, step_id: str, db: Session) -> Dict[str, Any]:
        """Compute before and after statistics for a specific pipeline step."""
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError("Dataset not found")

        steps = db.query(PipelineStep).filter(
            PipelineStep.dataset_id == dataset_id
        ).order_by(PipelineStep.step_order.asc()).all()

        target_step = None
        target_idx = -1
        for idx, s in enumerate(steps):
            if s.id == step_id:
                target_step = s
                target_idx = idx
                break

        if not target_step:
            raise ValueError(f"Step {step_id} not found")

        # Run up to target step
        df = DatasetProfiler.load_dataset(dataset.file_path)
        for i in range(target_idx):
            s = steps[i]
            if s.is_active:
                params = json.loads(s.params) if s.params else {}
                df = cls.apply_operation(df, s.operation, params)

        before_shape = [int(df.shape[0]), int(df.shape[1])]
        before_missing = int(df.isna().sum().sum())
        before_columns = df.columns.tolist()

        # Apply target step
        params = json.loads(target_step.params) if target_step.params else {}
        df_after = cls.apply_operation(df, target_step.operation, params)

        after_shape = [int(df_after.shape[0]), int(df_after.shape[1])]
        after_missing = int(df_after.isna().sum().sum())
        after_columns = df_after.columns.tolist()

        return {
            "step_id": step_id,
            "operation": target_step.operation,
            "is_active": target_step.is_active,
            "before": {
                "shape": before_shape,
                "total_missing": before_missing,
                "columns": before_columns
            },
            "after": {
                "shape": after_shape,
                "total_missing": after_missing,
                "columns": after_columns
            },
            "diff": {
                "rows_delta": after_shape[0] - before_shape[0],
                "cols_delta": after_shape[1] - before_shape[1],
                "missing_delta": after_missing - before_missing,
                "dropped_columns": list(set(before_columns) - set(after_columns)),
                "added_columns": list(set(after_columns) - set(before_columns))
            }
        }
