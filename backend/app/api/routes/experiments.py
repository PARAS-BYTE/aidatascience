"""Experiment API routes — Training, leaderboard, and experiment management."""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.db.database import get_db, SessionLocal
from app.db.models import Experiment, Job, JobStatus, JobType, ExperimentStatus
from app.schemas.dataset import (
    TrainingRequest, ExperimentResponse, LeaderboardResponse, JobResponse,
    EvaluationResponse,
)
from app.services.experiment_service import ExperimentService
from app.services.job_service import JobService
from app.core.logging import logger

router = APIRouter(prefix="/experiments", tags=["Experiments"])


def _run_training_background(job_id: str, request_data: dict):
    """Background task for model training."""
    db = SessionLocal()
    try:
        JobService.start_job(db, job_id)
        result = ExperimentService.run_training_pipeline(
            db=db,
            dataset_id=request_data["dataset_id"],
            target=request_data["target"],
            primary_metric=request_data.get("primary_metric"),
            test_size=request_data.get("test_size", 0.2),
            cv_folds=request_data.get("cv_folds", 5),
            random_seed=request_data.get("random_seed", 42),
            enable_feature_engineering=request_data.get("enable_feature_engineering", True),
            job_id=job_id,
            budget_seconds=request_data.get("budget_seconds"),
        )
        # Store result summary
        result_summary = {
            "task_type": result["task_type"],
            "primary_metric": result["primary_metric"],
            "n_experiments": len(result["experiments"]),
            "best_algorithm": result["leaderboard"][0]["algorithm"] if result["leaderboard"] else None,
            "best_score": result["leaderboard"][0]["primary_metric_value"] if result["leaderboard"] else None,
            "elimination_log": result.get("elimination_log", []),
            "survival_funnel": result.get("survival_funnel", []),
            "budget_seconds": result.get("budget_seconds"),
        }
        JobService.complete_job(db, job_id, result_data=json.dumps(result_summary))

        # Index experiments in Experiment Memory (B6)
        try:
            from app.services.experiment_memory_service import ExperimentMemoryService
            for exp_item in result.get("experiments", []):
                ExperimentMemoryService.index_experiment(db, exp_item["id"])
        except Exception as mem_err:
            logger.warning(f"Failed indexing experiment memory: {mem_err}")
    except Exception as e:
        logger.error(f"Training job {job_id} failed: {str(e)}", exc_info=True)
        JobService.fail_job(db, job_id, error_message=str(e))
    finally:
        db.close()


@router.post("/train", response_model=JobResponse)
def start_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start model training as a background job."""
    from app.db.models import Dataset
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    job = Job(
        job_type=JobType.TRAINING,
        status=JobStatus.QUEUED,
        dataset_id=request.dataset_id,
        progress_message="Queued for training",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_training_background,
        job.id,
        request.model_dump(),
    )

    return job


@router.get("", response_model=List[ExperimentResponse])
def list_experiments(dataset_id: str = None, db: Session = Depends(get_db)):
    """List all experiments, optionally filtered by dataset."""
    query = db.query(Experiment).order_by(Experiment.created_at.desc())
    if dataset_id:
        query = query.filter(Experiment.dataset_id == dataset_id)

    experiments = query.all()
    result = []
    for exp in experiments:
        result.append(ExperimentResponse(
            id=exp.id,
            name=exp.name,
            dataset_id=exp.dataset_id,
            target_column=exp.target_column,
            task_type=exp.task_type.value,
            algorithm=exp.algorithm,
            hyperparameters=json.loads(exp.hyperparameters) if exp.hyperparameters else None,
            metrics=json.loads(exp.metrics) if exp.metrics else None,
            cv_scores=json.loads(exp.cv_scores) if exp.cv_scores else None,
            primary_metric=exp.primary_metric,
            training_duration=exp.training_duration,
            status=exp.status.value,
            created_at=exp.created_at,
            completed_at=exp.completed_at,
        ))
    return result


@router.get("/leaderboard/{dataset_id}", response_model=LeaderboardResponse)
def get_leaderboard(dataset_id: str, db: Session = Depends(get_db)):
    """Get model leaderboard for a dataset."""
    result = ExperimentService.get_leaderboard(db, dataset_id)
    if not result["entries"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed experiments found for this dataset."
        )
    return result


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    """Get details of a specific experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        dataset_id=exp.dataset_id,
        target_column=exp.target_column,
        task_type=exp.task_type.value,
        algorithm=exp.algorithm,
        hyperparameters=json.loads(exp.hyperparameters) if exp.hyperparameters else None,
        metrics=json.loads(exp.metrics) if exp.metrics else None,
        cv_scores=json.loads(exp.cv_scores) if exp.cv_scores else None,
        primary_metric=exp.primary_metric,
        training_duration=exp.training_duration,
        status=exp.status.value,
        created_at=exp.created_at,
        completed_at=exp.completed_at,
    )


# ─── B7: Experiment Export Route ──────────────────────────────────────────────

from fastapi.responses import Response
from app.services.export_service import ExportService


@router.get("/{experiment_id}/export")
def export_experiment(experiment_id: str, format: str = "notebook", db: Session = Depends(get_db)):
    """Export experiment pipeline as an executable Python script (.py) or Jupyter Notebook (.ipynb)."""
    try:
        if format.lower() == "script":
            code = ExportService.generate_script(experiment_id, db)
            filename = f"pipeline_{experiment_id[:8]}.py"
            media_type = "text/x-python"
        else:
            code = ExportService.generate_notebook(experiment_id, db)
            filename = f"pipeline_{experiment_id[:8]}.ipynb"
            media_type = "application/x-ipynb+json"

        return Response(
            content=code,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/memory/similar")
def find_similar_experiments(query: str, top_k: int = 3, db: Session = Depends(get_db)):
    """Retrieve semantically nearest past experiment solutions (B6 Experiment Memory)."""
    try:
        from app.services.experiment_memory_service import ExperimentMemoryService
        return ExperimentMemoryService.find_similar(db, query=query, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

