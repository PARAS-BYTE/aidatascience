"""
Experiment Service — Orchestrates model training pipeline.
Connects cleaning → feature engineering → AutoML → evaluation.
"""
import os
import json
import time
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    Dataset, Experiment, MLModel, Job, JobStatus, JobType,
    ExperimentStatus, ModelStatus, TaskType,
)
from app.services.profiler import DatasetProfiler
from ml_engine.preprocessing.cleaning_engine import CleaningEngine
from ml_engine.preprocessing.feature_engine import FeatureEngineeringEngine
from ml_engine.analysis.task_detection import TaskDetectionEngine
from ml_engine.models.automl_engine import AutoMLEngine
from ml_engine.models.evaluation_engine import EvaluationEngine


class ExperimentService:
    """Manages the full experiment lifecycle from data to trained models."""

    @staticmethod
    def run_training_pipeline(
        db: Session,
        dataset_id: str,
        target: str,
        primary_metric: Optional[str] = None,
        test_size: float = 0.2,
        cv_folds: int = 5,
        random_seed: int = 42,
        enable_feature_engineering: bool = True,
        job_id: Optional[str] = None,
        budget_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full training pipeline:
        1. Load dataset
        2. Detect task
        3. Clean data
        4. Feature engineering
        5. Build preprocessing pipeline
        6. Train/test split
        7. Train models (AutoML)
        8. Evaluate on test set
        9. Save models and create experiment records
        """
        def update_job(progress: float, message: str):
            if job_id:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.progress = progress
                    job.progress_message = message
                    db.commit()

        try:
            update_job(5, "Loading dataset...")

            # 1. Load dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            df = DatasetProfiler.load_dataset(dataset.file_path)
            logger.info(f"Loaded dataset {dataset_id}: {df.shape}")

            # 2. Detect task
            update_job(10, "Detecting task type...")
            task_info = TaskDetectionEngine.detect_task(df, target)
            if task_info.get("error"):
                raise ValueError(task_info["error"])

            task_type = task_info["task"]
            logger.info(f"Detected task: {task_type} for target '{target}'")

            # Update dataset with target info
            dataset.target_column = target
            dataset.task_type = TaskType(task_type)
            db.commit()

            # Set default metric
            if primary_metric is None:
                if "classification" in task_type:
                    primary_metric = "f1"
                else:
                    primary_metric = "r2"

            # 3. Clean data
            update_job(20, "Cleaning data...")
            issues = CleaningEngine.detect_issues(df)
            cleaned_df, cleaning_report = CleaningEngine.clean_dataset(
                df, target=target,
                detected_ids=issues["potential_ids"],
            )
            logger.info(f"Cleaned: {cleaning_report['rows_before']} -> {cleaning_report['rows_after']} rows")

            # 4. Feature engineering
            feature_report = {}
            if enable_feature_engineering:
                update_job(30, "Engineering features...")
                cleaned_df, feature_report = FeatureEngineeringEngine.run_feature_engineering(
                    cleaned_df, target=target,
                )
                logger.info(f"Feature engineering: {feature_report.get('original_shape')} -> {feature_report.get('final_shape')}")

            # 5. Build preprocessing pipeline
            update_job(40, "Building preprocessing pipeline...")
            preprocessor, label_encoder, numerical_cols, categorical_cols = \
                CleaningEngine.build_preprocessing_pipeline(cleaned_df, target, task_type=task_type)

            # 6. Train/test split
            X_train, X_test, y_train, y_test = CleaningEngine.prepare_train_test(
                cleaned_df, target, test_size=test_size, random_seed=random_seed
            )

            # Fit preprocessor on training data only (prevents leakage)
            X_train_processed = preprocessor.fit_transform(X_train)
            X_test_processed = preprocessor.transform(X_test)

            # Encode target if needed
            if label_encoder is not None:
                label_encoder.fit(cleaned_df[target].dropna())
                y_train_encoded = label_encoder.transform(y_train)
                y_test_encoded = label_encoder.transform(y_test)
            else:
                y_train_encoded = y_train.values if hasattr(y_train, 'values') else y_train
                y_test_encoded = y_test.values if hasattr(y_test, 'values') else y_test

            # Get feature names after preprocessing
            feature_names = []
            if numerical_cols:
                feature_names.extend(numerical_cols)
            if categorical_cols:
                try:
                    ohe = preprocessor.named_transformers_.get("cat")
                    if ohe and hasattr(ohe, "named_steps"):
                        encoder = ohe.named_steps.get("encoder")
                        if encoder and hasattr(encoder, "get_feature_names_out"):
                            feature_names.extend(encoder.get_feature_names_out(categorical_cols).tolist())
                        else:
                            feature_names.extend(categorical_cols)
                    else:
                        feature_names.extend(categorical_cols)
                except Exception:
                    feature_names.extend(categorical_cols)

            # 7. Train models (Standard or Budget-Aware Successive Halving)
            update_job(50, "Training models...")
            if budget_seconds:
                training_results = AutoMLEngine.train_models_budget(
                    X_train_processed, y_train_encoded,
                    task_type=task_type,
                    budget_seconds=budget_seconds,
                    primary_metric=primary_metric,
                    cv_folds=cv_folds,
                    random_seed=random_seed,
                    progress_callback=lambda progress=0, message="": update_job(50 + progress * 0.3, message),
                )
                if job_id:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.budget_seconds = budget_seconds
                        job.elimination_log = json.dumps(training_results.get("elimination_log", []))
                        db.commit()
            else:
                training_results = AutoMLEngine.train_models(
                    X_train_processed, y_train_encoded,
                    task_type=task_type,
                    primary_metric=primary_metric,
                    cv_folds=cv_folds,
                    random_seed=random_seed,
                    progress_callback=lambda progress=0, message="": update_job(50 + progress * 0.3, message),
                )

            # 8. Evaluate and save each model
            update_job(85, "Evaluating models on test set...")
            experiments = []
            class_labels = None
            if label_encoder is not None:
                class_labels = label_encoder.classes_.tolist()

            for entry in training_results["leaderboard"]:
                if entry["status"] != "completed":
                    continue

                algorithm = entry["algorithm"]
                model = training_results["trained_models"][algorithm]

                # Evaluate on test set
                eval_results = EvaluationEngine.evaluate(
                    model, X_test_processed, y_test_encoded,
                    task_type=task_type,
                    class_labels=class_labels,
                )

                # Save model artifacts
                exp_id = f"{dataset_id}_{algorithm}_{int(time.time())}"
                save_dir = os.path.join(settings.MODEL_DIR, exp_id)
                os.makedirs(save_dir, exist_ok=True)

                model_path = AutoMLEngine.save_model(model, save_dir, algorithm)
                preprocessing_paths = CleaningEngine.save_preprocessing_artifacts(
                    preprocessor, label_encoder, numerical_cols, categorical_cols, save_dir
                )

                # Create experiment record
                experiment = Experiment(
                    name=f"{entry['display_name']} on {dataset.original_filename}",
                    user_id=dataset.user_id,
                    dataset_id=dataset_id,
                    target_column=target,
                    task_type=TaskType(task_type),
                    algorithm=algorithm,
                    hyperparameters=json.dumps(entry["hyperparameters"]),
                    preprocessing_config=json.dumps({
                        "numerical_cols": numerical_cols,
                        "categorical_cols": categorical_cols,
                        "cleaning": cleaning_report,
                        "features": feature_report,
                    }),
                    feature_config=json.dumps(feature_report) if feature_report else None,
                    primary_metric=primary_metric,
                    metrics=json.dumps(eval_results.get("metrics", entry["metrics"])),
                    cv_scores=json.dumps(entry.get("cv_scores", {})),
                    train_test_split=test_size,
                    random_seed=random_seed,
                    training_duration=entry["training_duration"],
                    model_artifact_path=model_path,
                    preprocessing_artifact_path=save_dir,
                    feature_names=json.dumps(feature_names),
                    status=ExperimentStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(experiment)
                db.flush()

                experiments.append({
                    "experiment_id": experiment.id,
                    "algorithm": algorithm,
                    "display_name": entry["display_name"],
                    "metrics": eval_results.get("metrics", entry["metrics"]),
                    "cv_metrics": entry["metrics"],
                    "training_duration": entry["training_duration"],
                    "evaluation": eval_results,
                })

            db.commit()
            update_job(100, "Training complete.")

            return {
                "dataset_id": dataset_id,
                "target": target,
                "task_type": task_type,
                "primary_metric": primary_metric,
                "experiments": experiments,
                "leaderboard": training_results["leaderboard"],
                "elimination_log": training_results.get("elimination_log", []),
                "survival_funnel": training_results.get("survival_funnel", []),
                "budget_seconds": budget_seconds,
                "cleaning_report": cleaning_report,
                "feature_report": feature_report,
            }

        except Exception as e:
            logger.error(f"Training pipeline failed: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_leaderboard(db: Session, dataset_id: str) -> Dict[str, Any]:
        """Get the model leaderboard for a dataset."""
        experiments = db.query(Experiment).filter(
            Experiment.dataset_id == dataset_id,
            Experiment.status == ExperimentStatus.COMPLETED,
        ).all()

        if not experiments:
            return {"entries": [], "primary_metric": None, "task_type": None}

        entries = []
        for exp in experiments:
            metrics = json.loads(exp.metrics) if exp.metrics else {}
            entries.append({
                "experiment_id": exp.id,
                "algorithm": exp.algorithm,
                "display_name": exp.name,
                "metrics": metrics,
                "primary_metric_value": metrics.get(exp.primary_metric, 0),
                "training_duration": exp.training_duration,
                "status": exp.status.value,
                "created_at": exp.created_at.isoformat(),
            })

        # Sort by primary metric
        primary_metric = experiments[0].primary_metric
        reverse = primary_metric not in ("mae", "mse", "rmse")
        entries.sort(key=lambda x: x["primary_metric_value"], reverse=reverse)
        for i, entry in enumerate(entries):
            entry["rank"] = i + 1

        return {
            "dataset_id": dataset_id,
            "target": experiments[0].target_column,
            "task_type": experiments[0].task_type.value,
            "primary_metric": primary_metric,
            "entries": entries,
        }
