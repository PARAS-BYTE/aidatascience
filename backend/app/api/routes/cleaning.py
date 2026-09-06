"""Cleaning API routes — Detect issues, preview and apply cleaning."""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Dataset, User
from app.api.deps import get_current_user
from app.services.profiler import DatasetProfiler
from app.schemas.dataset import CleaningIssues, CleaningRequest, CleaningResponse
from ml_engine.preprocessing.cleaning_engine import CleaningEngine

router = APIRouter(prefix="/datasets", tags=["Cleaning"])


@router.get("/{dataset_id}/cleaning-issues", response_model=CleaningIssues)
def get_cleaning_issues(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detect data quality issues without modifying the dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    df = DatasetProfiler.load_dataset(dataset.file_path)
    issues = CleaningEngine.detect_issues(df)
    return issues


@router.post("/{dataset_id}/clean", response_model=CleaningResponse)
def clean_dataset(
    dataset_id: str,
    request: CleaningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clean dataset and save cleaned version."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    df = DatasetProfiler.load_dataset(dataset.file_path)

    if request.target not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{request.target}' not found in dataset."
        )

    # Detect IDs for cleaning
    issues = CleaningEngine.detect_issues(df)

    cleaned_df, report = CleaningEngine.clean_dataset(
        df,
        target=request.target,
        drop_ids=request.drop_ids,
        drop_constants=request.drop_constants,
        remove_duplicates=request.remove_duplicates,
        handle_missing=request.handle_missing,
        detected_ids=issues["potential_ids"],
    )

    # Save cleaned version
    import os
    from app.core.config import settings
    from app.db.models import DatasetVersion

    cleaned_path = os.path.join(settings.PROCESSED_DIR, f"cleaned_{dataset.stored_filename}")
    cleaned_df.to_csv(cleaned_path, index=False)

    dataset.cleaned_file_path = cleaned_path
    dataset.target_column = request.target
    dataset.cleaning_config = json.dumps(report)
    dataset.version = (dataset.version or 1) + 1

    new_version = DatasetVersion(
        dataset_id=dataset.id,
        version=dataset.version,
        file_path=cleaned_path,
        file_size=os.path.getsize(cleaned_path) if os.path.exists(cleaned_path) else 0,
        row_count=len(cleaned_df),
        column_count=len(cleaned_df.columns),
        change_summary=f"Automated cleaning: {report.get('changes_made', ['Applied data cleaning'])[0] if isinstance(report.get('changes_made'), list) and report.get('changes_made') else 'Applied data cleaning'}",
    )
    db.add(new_version)
    db.commit()

    report["dataset_id"] = dataset_id
    return report


# ─── Pipeline Management Routes ───────────────────────────────────────────────

from app.db.models import PipelineStep
from app.services.pipeline_service import PipelineService
from app.schemas.dataset import PipelineStepCreate, PipelineStepUpdate, PipelineStepResponse


@router.get("/{dataset_id}/pipeline")
def get_pipeline_steps(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all pipeline steps for a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    steps = db.query(PipelineStep).filter(
        PipelineStep.dataset_id == dataset_id
    ).order_by(PipelineStep.step_order.asc()).all()

    return [
        {
            "id": s.id,
            "dataset_id": s.dataset_id,
            "step_order": s.step_order,
            "operation": s.operation,
            "params": json.loads(s.params) if s.params else {},
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in steps
    ]


@router.post("/{dataset_id}/pipeline")
def add_pipeline_step(
    dataset_id: str,
    step_data: PipelineStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new step to the cleaning pipeline."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Determine step order
    max_order = db.query(PipelineStep).filter(PipelineStep.dataset_id == dataset_id).count()

    new_step = PipelineStep(
        dataset_id=dataset_id,
        step_order=max_order + 1,
        operation=step_data.operation,
        params=json.dumps(step_data.params) if step_data.params else "{}",
        is_active=True
    )
    db.add(new_step)
    db.commit()
    db.refresh(new_step)

    # Replay automatically
    try:
        replay_result = PipelineService.replay_pipeline(dataset_id, db)
    except Exception as e:
        replay_result = {"error": str(e)}

    return {
        "step": {
            "id": new_step.id,
            "dataset_id": new_step.dataset_id,
            "step_order": new_step.step_order,
            "operation": new_step.operation,
            "params": json.loads(new_step.params) if new_step.params else {},
            "is_active": new_step.is_active,
            "created_at": new_step.created_at.isoformat() if new_step.created_at else None
        },
        "replay": replay_result
    }


@router.patch("/{dataset_id}/pipeline/{step_id}")
def update_pipeline_step(
    dataset_id: str,
    step_id: str,
    update_data: PipelineStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle or update a pipeline step."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    step = db.query(PipelineStep).filter(
        PipelineStep.id == step_id,
        PipelineStep.dataset_id == dataset_id
    ).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline step not found")

    if update_data.is_active is not None:
        step.is_active = update_data.is_active
    if update_data.step_order is not None:
        step.step_order = update_data.step_order
    if update_data.params is not None:
        step.params = json.dumps(update_data.params)

    db.commit()
    db.refresh(step)

    # Replay pipeline after toggle
    replay_result = PipelineService.replay_pipeline(dataset_id, db)

    return {
        "step": {
            "id": step.id,
            "dataset_id": step.dataset_id,
            "step_order": step.step_order,
            "operation": step.operation,
            "params": json.loads(step.params) if step.params else {},
            "is_active": step.is_active,
            "created_at": step.created_at.isoformat() if step.created_at else None
        },
        "replay": replay_result
    }


@router.delete("/{dataset_id}/pipeline/{step_id}")
def delete_pipeline_step(
    dataset_id: str,
    step_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a step from the pipeline."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    step = db.query(PipelineStep).filter(
        PipelineStep.id == step_id,
        PipelineStep.dataset_id == dataset_id
    ).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline step not found")

    db.delete(step)
    db.commit()

    # Re-order remaining steps
    remaining = db.query(PipelineStep).filter(
        PipelineStep.dataset_id == dataset_id
    ).order_by(PipelineStep.step_order.asc()).all()

    for idx, s in enumerate(remaining):
        s.step_order = idx + 1
    db.commit()

    replay_result = PipelineService.replay_pipeline(dataset_id, db)
    return {"message": "Step deleted", "replay": replay_result}


@router.post("/{dataset_id}/pipeline/replay")
def replay_pipeline_endpoint(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-execute all active pipeline steps from the raw dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    result = PipelineService.replay_pipeline(dataset_id, db)
    return result


@router.get("/{dataset_id}/pipeline/{step_id}/diff")
def get_pipeline_step_diff(
    dataset_id: str,
    step_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get before and after stats for a specific step."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    try:
        diff = PipelineService.get_step_diff(dataset_id, step_id, db)
        return diff
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
