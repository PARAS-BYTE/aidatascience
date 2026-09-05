"""
Model Service — Model registry, prediction, and lifecycle management.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    Experiment, MLModel, Deployment, ExperimentStatus,
    ModelStatus, DeploymentStatus,
)
from ml_engine.preprocessing.cleaning_engine import CleaningEngine
from ml_engine.models.automl_engine import AutoMLEngine
from ml_engine.models.evaluation_engine import EvaluationEngine
from ml_engine.models.explainability_engine import ExplainabilityEngine


class ModelService:
    """Manages model registry, prediction, and deployment."""

    @staticmethod
    def register_model(db: Session, experiment_id: str, name: Optional[str] = None) -> MLModel:
        """Register a trained experiment as a model in the registry."""
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status != ExperimentStatus.COMPLETED:
            raise ValueError(f"Experiment {experiment_id} is not completed")

        # Check if model already exists for this experiment
        existing = db.query(MLModel).filter(MLModel.experiment_id == experiment_id).first()
        if existing:
            return existing

        model_name = name or experiment.name

        # Determine next version
        existing_models = db.query(MLModel).filter(
            MLModel.name == model_name
        ).count()
        version = existing_models + 1

        ml_model = MLModel(
            name=model_name,
            version=version,
            experiment_id=experiment_id,
            dataset_id=experiment.dataset_id,
            task_type=experiment.task_type,
            target_column=experiment.target_column,
            algorithm=experiment.algorithm,
            hyperparameters=experiment.hyperparameters,
            metrics=experiment.metrics,
            feature_names=experiment.feature_names,
            artifact_path=experiment.model_artifact_path,
            preprocessing_path=experiment.preprocessing_artifact_path,
            status=ModelStatus.TRAINED,
        )

        db.add(ml_model)
        db.commit()
        db.refresh(ml_model)

        # Auto-compute SHAP on registration & save Parquet (B3)
        try:
            ModelService.get_explainability(db, ml_model.id)
        except Exception as shap_err:
            logger.warning(f"SHAP auto-computation skipped during registration: {shap_err}")

        logger.info(f"Registered model '{model_name}' v{version} from experiment {experiment_id}")
        return ml_model

    @staticmethod
    def predict(db: Session, model_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make a prediction using a registered model."""
        model_record = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model_record:
            raise ValueError(f"Model {model_id} not found")

        # Load model and preprocessing pipeline
        model = joblib.load(model_record.artifact_path)
        preprocessor, label_encoder, meta = CleaningEngine.load_preprocessing_artifacts(
            model_record.preprocessing_path
        )

        # Build input DataFrame
        feature_df = pd.DataFrame([features])

        # Ensure correct columns
        numerical_cols = meta.get("numerical_columns", [])
        categorical_cols = meta.get("categorical_columns", [])
        expected_cols = numerical_cols + categorical_cols

        # Fill missing columns with NaN
        for col in expected_cols:
            if col not in feature_df.columns:
                feature_df[col] = np.nan

        # Reorder to match training
        feature_df = feature_df[expected_cols]

        # Transform
        X = preprocessor.transform(feature_df)

        # Predict
        prediction_raw = model.predict(X)[0]
        probability = None

        if hasattr(model, "predict_proba"):
            try:
                proba = model.predict_proba(X)[0]
                probability = round(float(max(proba)), 4)
            except Exception:
                pass

        # Decode label if needed
        if label_encoder is not None:
            try:
                prediction = label_encoder.inverse_transform([int(prediction_raw)])[0]
            except Exception:
                prediction = prediction_raw
        else:
            prediction = prediction_raw

        if isinstance(prediction, (np.integer, np.floating)):
            prediction = round(float(prediction), 4)

        return {
            "prediction": prediction,
            "probability": probability,
            "model_id": model_id,
            "model_version": model_record.version,
        }

    @staticmethod
    def get_explainability(db: Session, model_id: str) -> Dict[str, Any]:
        """Compute SHAP-based feature importance for a model."""
        model_record = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model_record:
            raise ValueError(f"Model {model_id} not found")

        # Check cached explainability
        if model_record.explainability_data:
            try:
                return json.loads(model_record.explainability_data)
            except Exception:
                pass

        # Load model and data
        model = joblib.load(model_record.artifact_path)
        feature_names = json.loads(model_record.feature_names) if model_record.feature_names else []

        # Load experiment to get training data for SHAP background
        experiment = db.query(Experiment).filter(Experiment.id == model_record.experiment_id).first()
        if not experiment:
            raise ValueError("Cannot find associated experiment")

        from app.services.profiler import DatasetProfiler
        from app.db.models import Dataset
        dataset = db.query(Dataset).filter(Dataset.id == model_record.dataset_id).first()
        if not dataset:
            raise ValueError("Cannot find associated dataset")

        df = DatasetProfiler.load_dataset(dataset.file_path)

        # Rebuild preprocessing and align features
        preprocessor, label_encoder, meta = CleaningEngine.load_preprocessing_artifacts(
            model_record.preprocessing_path
        )

        from ml_engine.preprocessing.feature_engine import FeatureEngineeringEngine
        target = experiment.target_column
        issues = CleaningEngine.detect_issues(df)
        processed_df, _ = CleaningEngine.clean_dataset(df, target=target, detected_ids=issues.get("potential_ids", []))
        if experiment.feature_config:
            processed_df, _ = FeatureEngineeringEngine.run_feature_engineering(processed_df, target=target)

        # Prepare features
        feature_cols = meta.get("numerical_columns", []) + meta.get("categorical_columns", [])
        available_cols = [c for c in feature_cols if c in processed_df.columns]
        X_raw = processed_df[available_cols].head(500)
        X_processed = preprocessor.transform(X_raw)

        # Compute SHAP
        result = ExplainabilityEngine.compute_global_importance(
            model, X_processed, feature_names, max_samples=500
        )

        # Store SHAP matrix as Parquet (B3)
        try:
            os.makedirs(settings.MODELS_DIR, exist_ok=True)
            parquet_path = os.path.join(settings.MODELS_DIR, f"shap_{model_id}.parquet")
            shap_df = pd.DataFrame(result.get("feature_importance", []))
            shap_df.to_parquet(parquet_path, index=False)
            result["parquet_path"] = parquet_path
        except Exception as p_err:
            logger.warning(f"Could not persist SHAP parquet: {p_err}")

        # Cache result
        model_record.explainability_data = json.dumps(result)
        db.commit()

        return result

    @staticmethod
    def explain_prediction(
        db: Session, model_id: str, features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Explain a single prediction using SHAP."""
        model_record = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model_record:
            raise ValueError(f"Model {model_id} not found")

        model = joblib.load(model_record.artifact_path)
        preprocessor, label_encoder, meta = CleaningEngine.load_preprocessing_artifacts(
            model_record.preprocessing_path
        )
        feature_names = json.loads(model_record.feature_names) if model_record.feature_names else []

        # Build input
        feature_df = pd.DataFrame([features])
        numerical_cols = meta.get("numerical_columns", [])
        categorical_cols = meta.get("categorical_columns", [])
        expected_cols = numerical_cols + categorical_cols

        for col in expected_cols:
            if col not in feature_df.columns:
                feature_df[col] = np.nan
        feature_df = feature_df[expected_cols]

        X = preprocessor.transform(feature_df)

        result = ExplainabilityEngine.explain_prediction(
            model, X[0], feature_names
        )

        # Decode label if needed
        if label_encoder is not None and "prediction" in result:
            try:
                raw_pred = result["prediction"]
                if isinstance(raw_pred, str) and raw_pred.replace(".", "").replace("-", "").isdigit():
                    decoded = label_encoder.inverse_transform([int(float(raw_pred))])[0]
                    result["prediction"] = str(decoded)
            except Exception:
                pass

        return result

    @staticmethod
    def deploy_model(db: Session, model_id: str, role: str = "champion", traffic_pct: float = 1.0) -> Deployment:
        """Deploy a model with champion/challenger role and traffic allocation."""
        model_record = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model_record:
            raise ValueError(f"Model {model_id} not found")

        # Check for existing deployment of this model
        existing = db.query(Deployment).filter(
            Deployment.model_id == model_id,
            Deployment.status == DeploymentStatus.ACTIVE,
        ).first()
        if existing:
            existing.role = role
            existing.traffic_pct = traffic_pct
            db.commit()
            return existing

        model_record.status = ModelStatus.PRODUCTION
        endpoint = f"/api/models/{model_id}/predict"

        deployment = Deployment(
            model_id=model_id,
            model_version=model_record.version,
            endpoint=endpoint,
            status=DeploymentStatus.ACTIVE,
            role=role,
            traffic_pct=traffic_pct,
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)

        # Auto-generate Model Card upon deployment
        try:
            from app.services.model_card_service import ModelCardService
            ModelCardService.generate_card(model_id, db)
        except Exception as e:
            logger.warning(f"Could not auto-generate model card: {e}")

        logger.info(f"Deployed model {model_id} as {role} ({traffic_pct*100}% traffic) at {endpoint}")
        return deployment

    @staticmethod
    def promote_challenger(db: Session, deployment_id: str) -> Deployment:
        """Promote a challenger deployment to champion, demoting current champion to challenger."""
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        target_model = db.query(MLModel).filter(MLModel.id == deployment.model_id).first()
        if not target_model:
            raise ValueError("Associated model not found")

        # Find existing champion on the same dataset/target
        other_deployments = db.query(Deployment).join(MLModel).filter(
            MLModel.dataset_id == target_model.dataset_id,
            Deployment.id != deployment_id,
            Deployment.status == DeploymentStatus.ACTIVE,
            Deployment.role == "champion"
        ).all()

        for old_champ in other_deployments:
            old_champ.role = "challenger"
            old_champ.traffic_pct = 0.2

        deployment.role = "champion"
        deployment.traffic_pct = 1.0
        db.commit()
        db.refresh(deployment)

        logger.info(f"Promoted deployment {deployment_id} to champion")
        return deployment

    @staticmethod
    def update_model_status(db: Session, model_id: str, status: str) -> MLModel:
        """Update model status (promote, archive, etc.)."""
        model_record = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model_record:
            raise ValueError(f"Model {model_id} not found")

        model_record.status = ModelStatus(status)
        db.commit()
        db.refresh(model_record)
        return model_record
