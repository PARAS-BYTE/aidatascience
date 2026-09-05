"""
Feature Engineering API Routes — Interactive feature transformation and PCA preview.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
import os
import uuid

from app.db.database import get_db
from app.db.models import Dataset
from app.schemas.dataset import (
    FeatureEngineeringPreviewRequest,
    FeatureEngineeringPreviewResponse,
)
from app.services.profiler import DatasetProfiler
from app.core.logging import logger
from ml_engine.preprocessing.feature_engine import FeatureEngineeringEngine
from ml_engine.preprocessing.cleaning_engine import CleaningEngine

router = APIRouter(tags=["Feature Engineering"])


@router.post(
    "/datasets/{dataset_id}/feature-engineering/preview",
    response_model=FeatureEngineeringPreviewResponse,
)
def preview_feature_engineering(
    dataset_id: str,
    request: FeatureEngineeringPreviewRequest,
    db: Session = Depends(get_db),
):
    """
    Generate an interactive preview of engineered features, including PCA,
    polynomial terms, interaction products, and temporal decompositions.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )

    try:
        df = DatasetProfiler.load_dataset(dataset.file_path)

        # Pre-clean dataset
        issues = CleaningEngine.detect_issues(df)
        target = request.target
        cleaned_df, _ = CleaningEngine.clean_dataset(
            df,
            target=target,
            detected_ids=issues.get("potential_ids", []),
        )

        preview_data = FeatureEngineeringEngine.preview_feature_engineering(
            df=cleaned_df,
            target=target,
            enable_date_features=request.enable_date_features,
            enable_interactions=request.enable_interactions,
            max_interactions=request.max_interactions,
            enable_polynomial=request.enable_polynomial,
            polynomial_degree=request.polynomial_degree,
            enable_pca=request.enable_pca,
            pca_components=request.pca_components,
            drop_pca_original=request.drop_pca_original,
            preview_limit=request.preview_limit,
        )

        return FeatureEngineeringPreviewResponse(
            dataset_id=dataset_id,
            original_shape=preview_data["original_shape"],
            transformed_shape=preview_data["transformed_shape"],
            original_columns=preview_data["original_columns"],
            transformed_columns=preview_data["transformed_columns"],
            new_features=preview_data["new_features"],
            steps=preview_data["steps"],
            pca_report=preview_data.get("pca_report"),
            target_correlations=preview_data.get("target_correlations", {}),
            original_preview=preview_data["original_preview"],
            transformed_preview=preview_data["transformed_preview"],
        )

    except Exception as e:
        logger.error(f"Feature engineering preview failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feature engineering preview failed: {str(e)}",
        )


@router.post(
    "/datasets/{dataset_id}/feature-engineering/apply",
    response_model=dict,
)
def apply_feature_engineering(
    dataset_id: str,
    request: FeatureEngineeringPreviewRequest,
    db: Session = Depends(get_db),
):
    """
    Execute feature engineering and persist transformed dataset to disk for model training.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )

    try:
        import json
        from app.core.config import settings

        df = DatasetProfiler.load_dataset(dataset.file_path)
        target = request.target or dataset.target_column

        # Pre-clean dataset
        issues = CleaningEngine.detect_issues(df)
        cleaned_df, _ = CleaningEngine.clean_dataset(
            df,
            target=target,
            detected_ids=issues.get("potential_ids", []),
        )

        transformed_df, report = FeatureEngineeringEngine.run_feature_engineering(
            df=cleaned_df,
            target=target,
            enable_date_features=request.enable_date_features,
            enable_interactions=request.enable_interactions,
            max_interactions=request.max_interactions,
            enable_polynomial=request.enable_polynomial,
            polynomial_degree=request.polynomial_degree,
            enable_pca=request.enable_pca,
            pca_components=request.pca_components,
            drop_pca_original=request.drop_pca_original,
        )

        os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
        engineered_path = os.path.join(settings.PROCESSED_DIR, f"engineered_{dataset.stored_filename}")
        transformed_df.to_csv(engineered_path, index=False)

        dataset.cleaned_file_path = engineered_path
        dataset.feature_config = json.dumps(report)
        if target:
            dataset.target_column = target
        db.commit()

        return {
            "dataset_id": dataset_id,
            "original_shape": report["original_shape"],
            "transformed_shape": report["final_shape"],
            "original_columns": report["original_columns"],
            "transformed_columns": report["final_columns"],
            "new_features": report["new_features"],
            "steps": report["steps"],
            "pca_report": report.get("pca_report"),
            "file_path": engineered_path,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Feature engineering apply failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feature engineering apply failed: {str(e)}",
        )


@router.post(
    "/datasets/{dataset_id}/feature-engineering/auto-generate",
    response_model=dict,
)
def auto_generate_features(
    dataset_id: str,
    target: str = None,
    db: Session = Depends(get_db),
):
    """
    Auto-generate candidate features (interactions, ratios, temporal, non-linear)
    with estimated impact scores and mathematical formulas.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )

    try:
        df = DatasetProfiler.load_dataset(dataset.cleaned_file_path or dataset.file_path)
        effective_target = target or dataset.target_column

        candidates = FeatureEngineeringEngine.generate_candidates(df, target=effective_target)
        return {
            "dataset_id": dataset_id,
            "target": effective_target,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }
    except Exception as e:
        logger.error(f"Auto feature generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auto feature generation failed: {str(e)}",
        )

