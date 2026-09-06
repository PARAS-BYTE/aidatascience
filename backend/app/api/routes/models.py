"""Model API routes — Registry, prediction, explainability, deployment, monitoring."""
import json
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db, SessionLocal
from app.db.models import (
    MLModel, Deployment, DeploymentStatus, ModelStatus,
    ExperimentStatus, Job, JobStatus, JobType, User,
)
from app.api.deps import get_current_user, get_optional_user
from app.schemas.dataset import (
    ModelResponse, ModelListResponse, PredictionRequest, PredictionResponse,
    DeploymentRequest, DeploymentResponse, DeploymentListResponse,
    ExplainabilityResponse, PredictionExplanation,
    ModelHealthResponse, OptimizationRequest, OptimizationResponse,
    JobResponse,
)
from app.services.model_service import ModelService
from app.services.monitoring_service import MonitoringService
from app.services.job_service import JobService
from app.db.models import Job, JobStatus, JobType
from app.core.logging import logger

router = APIRouter(tags=["Models"])


# ─── Model Registry ─────────────────────────────────────────────────

@router.post("/models/register", response_model=ModelResponse)
def register_model(
    experiment_id: str,
    name: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a completed experiment owned by the user as a model."""
    try:
        model = ModelService.register_model(db, experiment_id, name, user_id=current_user.id)
        return _model_to_response(model)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/models", response_model=ModelListResponse)
def list_models(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List all registered models for the authenticated user only."""
    if not current_user:
        return ModelListResponse(total=0, items=[])
    models = db.query(MLModel).filter(MLModel.user_id == current_user.id).order_by(MLModel.created_at.desc()).all()
    return ModelListResponse(
        total=len(models),
        items=[_model_to_response(m) for m in models],
    )


@router.get("/dashboard")
@router.get("/models/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get dashboard statistics for the authenticated user."""
    from app.db.models import Dataset, Experiment

    if not current_user:
        return {
            "datasets": 0,
            "experiments": 0,
            "models": 0,
            "deployed_models": 0,
            "recent_datasets": [],
            "recent_experiments": [],
        }

    uid = current_user.id
    datasets = db.query(Dataset).filter(Dataset.user_id == uid).count()
    experiments = db.query(Experiment).filter(
        Experiment.user_id == uid,
        Experiment.status == ExperimentStatus.COMPLETED
    ).count()
    models = db.query(MLModel).filter(MLModel.user_id == uid).count()
    deployed = db.query(Deployment).join(MLModel).filter(
        MLModel.user_id == uid,
        Deployment.status == DeploymentStatus.ACTIVE
    ).count()

    recent_datasets = db.query(Dataset).filter(Dataset.user_id == uid).order_by(Dataset.created_at.desc()).limit(5).all()
    recent_experiments = db.query(Experiment).filter(Experiment.user_id == uid).order_by(Experiment.created_at.desc()).limit(5).all()

    return {
        "datasets": datasets,
        "experiments": experiments,
        "models": models,
        "deployed_models": deployed,
        "recent_datasets": [
            {"id": d.id, "name": d.original_filename, "created_at": d.created_at.isoformat()}
            for d in recent_datasets
        ],
        "recent_experiments": [
            {
                "id": e.id, "name": e.name, "algorithm": e.algorithm,
                "status": e.status.value, "created_at": e.created_at.isoformat(),
                "metrics": json.loads(e.metrics) if e.metrics else None,
            }
            for e in recent_experiments
        ],
    }


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific model owned by the current user."""
    model = db.query(MLModel).filter(MLModel.id == model_id, MLModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return _model_to_response(model)


@router.get("/models/{model_id}/card")
def get_model_card(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve or generate the standardized Markdown Model Card for a model owned by current user."""
    model = db.query(MLModel).filter(MLModel.id == model_id, MLModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    from app.services.model_card_service import ModelCardService
    try:
        content_md = ModelCardService.get_card(model_id, db)
        return {"model_id": model_id, "content_md": content_md}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/models/{model_id}/status")
def update_model_status(
    model_id: str,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update model status (promote, archive, etc.) for a model owned by current user."""
    try:
        model = ModelService.update_model_status(db, model_id, new_status, user_id=current_user.id)
        return _model_to_response(model)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── Prediction ──────────────────────────────────────────────────────

@router.post("/models/{model_id}/predict", response_model=PredictionResponse)
def predict(
    model_id: str,
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Make a prediction using a registered model owned by current user."""
    try:
        result = ModelService.predict(db, model_id, request.features, user_id=current_user.id)

        # Log prediction for monitoring
        deployment = db.query(Deployment).filter(
            Deployment.model_id == model_id,
            Deployment.status == DeploymentStatus.ACTIVE,
        ).first()

        MonitoringService.log_prediction(
            db, model_id, request.features,
            result["prediction"], result.get("probability"),
            deployment_id=deployment.id if deployment else None,
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prediction failed")


# ─── Explainability ──────────────────────────────────────────────────

@router.get("/models/{model_id}/explainability", response_model=ExplainabilityResponse)
def get_explainability(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get SHAP-based global feature importance for a model owned by current user."""
    try:
        result = ModelService.get_explainability(db, model_id, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Explainability failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Explainability computation failed")


@router.post("/models/{model_id}/explain-prediction", response_model=PredictionExplanation)
def explain_prediction(
    model_id: str,
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explain a single prediction using SHAP values for a model owned by current user."""
    try:
        result = ModelService.explain_prediction(db, model_id, request.features, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── Deployment ──────────────────────────────────────────────────────

@router.post("/deployments", response_model=DeploymentResponse)
def deploy_model(
    request: DeploymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deploy a model for serving predictions (supports champion/challenger roles)."""
    try:
        deployment = ModelService.deploy_model(
            db, request.model_id,
            role=request.role or "champion",
            traffic_pct=request.traffic_pct if request.traffic_pct is not None else 1.0,
            user_id=current_user.id,
        )
        return deployment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/deployments/{deployment_id}/promote", response_model=DeploymentResponse)
def promote_challenger_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Promote a challenger deployment to champion."""
    deployment = db.query(Deployment).join(MLModel).filter(
        Deployment.id == deployment_id,
        MLModel.user_id == current_user.id,
    ).first()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    try:
        return ModelService.promote_challenger(db, deployment_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/deployments", response_model=DeploymentListResponse)
def list_deployments(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List all deployments owned by the current user."""
    if not current_user:
        return DeploymentListResponse(total=0, items=[])
    deployments = db.query(Deployment).join(MLModel).filter(
        MLModel.user_id == current_user.id
    ).order_by(Deployment.created_at.desc()).all()
    return DeploymentListResponse(total=len(deployments), items=deployments)


@router.delete("/deployments/{deployment_id}")
def stop_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop a deployment."""
    deployment = db.query(Deployment).join(MLModel).filter(
        Deployment.id == deployment_id,
        MLModel.user_id == current_user.id,
    ).first()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    deployment.status = DeploymentStatus.STOPPED
    model = db.query(MLModel).filter(MLModel.id == deployment.model_id, MLModel.user_id == current_user.id).first()
    if model and model.status == ModelStatus.PRODUCTION:
        model.status = ModelStatus.VALIDATED
    db.commit()

    return {"message": f"Deployment {deployment_id} stopped."}


# ─── Monitoring ──────────────────────────────────────────────────────

@router.get("/monitoring/{model_id}", response_model=ModelHealthResponse)
def get_model_health(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model health including drift detection for a model owned by current user."""
    model = db.query(MLModel).filter(MLModel.id == model_id, MLModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    try:
        return MonitoringService.get_model_health(db, model_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/monitoring/{model_id}/drift")
def compute_drift(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger drift detection for a deployed model owned by current user."""
    model = db.query(MLModel).filter(MLModel.id == model_id, MLModel.user_id == current_user.id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    try:
        return MonitoringService.compute_drift(db, model_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/monitoring/alerts")
def get_alerts(model_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get active monitoring and drift alerts."""
    try:
        return MonitoringService.get_alerts(db, model_id=model_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/monitoring/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    """Resolve an alert."""
    try:
        return MonitoringService.resolve_alert(db, alert_id=alert_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



# ─── Optimization ───────────────────────────────────────────────────

@router.post("/optimization", response_model=JobResponse)
def start_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start hyperparameter optimization as a background job for a model owned by current user."""
    from app.db.models import Experiment
    experiment = db.query(Experiment).filter(Experiment.id == request.experiment_id, Experiment.user_id == current_user.id).first()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    job = Job(
        job_type=JobType.OPTIMIZATION,
        status=JobStatus.QUEUED,
        user_id=current_user.id,
        dataset_id=experiment.dataset_id,
        experiment_id=request.experiment_id,
        progress_message="Queued for optimization",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_optimization_background,
        job.id,
        request.model_dump(),
    )

    return job


def _run_optimization_background(job_id: str, request_data: dict):
    """Background task for hyperparameter optimization."""
    db = SessionLocal()
    try:
        JobService.start_job(db, job_id)

        from app.db.models import Experiment
        from ml_engine.models.optimization_engine import OptimizationEngine
        from ml_engine.preprocessing.cleaning_engine import CleaningEngine
        from app.services.profiler import DatasetProfiler
        from app.db.models import Dataset

        experiment = db.query(Experiment).filter(Experiment.id == request_data["experiment_id"]).first()
        if not experiment:
            raise ValueError("Experiment not found")

        dataset = db.query(Dataset).filter(Dataset.id == experiment.dataset_id).first()
        df = DatasetProfiler.load_dataset(dataset.file_path)

        # Rebuild preprocessing pipeline
        issues = CleaningEngine.detect_issues(df)
        cleaned_df, _ = CleaningEngine.clean_dataset(
            df, target=experiment.target_column,
            detected_ids=issues["potential_ids"],
        )

        preprocessor, label_encoder, num_cols, cat_cols = CleaningEngine.build_preprocessing_pipeline(
            cleaned_df, experiment.target_column
        )

        X_train, X_test, y_train, y_test = CleaningEngine.prepare_train_test(
            cleaned_df, experiment.target_column,
            test_size=experiment.train_test_split,
            random_seed=experiment.random_seed,
        )

        X_train_processed = preprocessor.fit_transform(X_train)
        if label_encoder:
            y_train_encoded = label_encoder.fit_transform(y_train)
        else:
            y_train_encoded = y_train.values

        # Run optimization
        metric = request_data.get("metric") or experiment.primary_metric
        opt_result = OptimizationEngine.optimize(
            X_train_processed, y_train_encoded,
            algorithm=request_data["algorithm"],
            task_type=experiment.task_type.value,
            metric=metric,
            n_trials=request_data.get("n_trials", 50),
            timeout=request_data.get("timeout", 300),
            random_seed=experiment.random_seed,
            progress_callback=lambda p, m: _update_job_progress(db, job_id, p, m),
        )

        # Save optimized model as new experiment
        import os, time as time_module
        from app.core.config import settings
        from ml_engine.models.automl_engine import AutoMLEngine
        from ml_engine.models.evaluation_engine import EvaluationEngine
        from app.db.models import ExperimentStatus, TaskType
        from datetime import datetime, timezone

        opt_model = opt_result["best_model"]
        X_test_processed = preprocessor.transform(X_test)
        if label_encoder:
            y_test_encoded = label_encoder.transform(y_test)
        else:
            y_test_encoded = y_test.values

        eval_results = EvaluationEngine.evaluate(
            opt_model, X_test_processed, y_test_encoded,
            task_type=experiment.task_type.value,
        )

        save_dir = os.path.join(settings.MODEL_DIR, f"opt_{experiment.id}_{int(time_module.time())}")
        model_path = AutoMLEngine.save_model(opt_model, save_dir, f"optimized_{request_data['algorithm']}")
        CleaningEngine.save_preprocessing_artifacts(preprocessor, label_encoder, num_cols, cat_cols, save_dir)

        feature_names_json = experiment.feature_names

        new_exp = Experiment(
            name=f"Optimized {request_data['algorithm']} ({opt_result['n_trials_completed']} trials)",
            user_id=experiment.user_id,
            dataset_id=experiment.dataset_id,
            target_column=experiment.target_column,
            task_type=experiment.task_type,
            algorithm=f"{request_data['algorithm']}_optimized",
            hyperparameters=json.dumps(opt_result["best_params"]),
            preprocessing_config=experiment.preprocessing_config,
            primary_metric=metric,
            metrics=json.dumps(eval_results.get("metrics", {})),
            train_test_split=experiment.train_test_split,
            random_seed=experiment.random_seed,
            training_duration=opt_result["duration"],
            model_artifact_path=model_path,
            preprocessing_artifact_path=save_dir,
            feature_names=feature_names_json,
            status=ExperimentStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(new_exp)
        db.flush()

        import json as json_module
        result_summary = json_module.dumps({
            "best_score": opt_result["best_score"],
            "best_params": opt_result["best_params"],
            "n_trials": opt_result["n_trials_completed"],
            "experiment_id": new_exp.id,
            "metrics": eval_results.get("metrics", {}),
        })

        JobService.complete_job(db, job_id, result_data=result_summary)
    except Exception as e:
        logger.error(f"Optimization job {job_id} failed: {str(e)}", exc_info=True)
        JobService.fail_job(db, job_id, error_message=str(e))
    finally:
        db.close()


def _update_job_progress(db: Session, job_id: str, progress: float, message: str):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.progress = progress
        job.progress_message = message
        db.commit()


def _model_to_response(model: MLModel) -> ModelResponse:
    return ModelResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        experiment_id=model.experiment_id,
        dataset_id=model.dataset_id,
        task_type=model.task_type.value,
        target_column=model.target_column,
        algorithm=model.algorithm,
        hyperparameters=json.loads(model.hyperparameters) if model.hyperparameters else None,
        metrics=json.loads(model.metrics) if model.metrics else None,
        status=model.status.value,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
