"""
Forecasting Service — Wraps ForecastingEngine with dataset loading and error handling.
"""
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Dataset
from app.services.profiler import DatasetProfiler
from ml_engine.models.forecasting_engine import ForecastingEngine
from app.core.logging import logger


class ForecastingService:
    @staticmethod
    def run_forecast(
        db: Session,
        dataset_id: str,
        user_id: Optional[str] = None,
        date_column: Optional[str] = None,
        value_column: Optional[str] = None,
        horizon: int = 14,
    ) -> Dict[str, Any]:
        query = db.query(Dataset).filter(Dataset.id == dataset_id)
        if user_id:
            query = query.filter(Dataset.user_id == user_id)
        dataset = query.first()
        if not dataset:
            raise ValueError(f"Dataset with ID '{dataset_id}' not found.")

        file_path = dataset.cleaned_file_path or dataset.file_path
        df = DatasetProfiler.load_dataset(file_path)

        result = ForecastingEngine.forecast(
            df=df,
            date_column=date_column,
            value_column=value_column,
            horizon=horizon,
        )
        result["dataset_id"] = dataset_id
        result["dataset_name"] = dataset.original_filename
        return result
