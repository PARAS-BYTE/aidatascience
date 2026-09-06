"""Task detection routes — Target suggestion and task type detection."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Dataset, TaskType, User
from app.api.deps import get_current_user
from app.services.profiler import DatasetProfiler
from app.schemas.dataset import TargetSuggestion, TaskDetectionResponse
from ml_engine.analysis.task_detection import TaskDetectionEngine

router = APIRouter(prefix="/datasets", tags=["Task Detection"])


@router.get("/{dataset_id}/suggest-target", response_model=List[TargetSuggestion])
def suggest_target(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest potential target columns using deterministic heuristics."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    df = DatasetProfiler.load_dataset(dataset.file_path)
    suggestions = TaskDetectionEngine.suggest_target(df)
    return suggestions


@router.post("/{dataset_id}/detect-task", response_model=TaskDetectionResponse)
def detect_task(
    dataset_id: str,
    target: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detect the ML task type for a given target column."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    df = DatasetProfiler.load_dataset(dataset.file_path)
    result = TaskDetectionEngine.detect_task(df, target)

    if result.get("task"):
        dataset.target_column = target
        dataset.task_type = TaskType(result["task"])
        db.commit()

    return result
