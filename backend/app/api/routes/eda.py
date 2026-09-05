"""EDA API routes — Trigger and retrieve exploratory data analysis."""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Dataset
from app.services.profiler import DatasetProfiler
from app.services.insight_service import InsightService
from app.schemas.dataset import EDAResponse
from ml_engine.analysis.eda_engine import EDAEngine

router = APIRouter(prefix="/datasets", tags=["EDA"])


@router.post("/{dataset_id}/eda", response_model=EDAResponse)
def run_eda(dataset_id: str, target: str = None, db: Session = Depends(get_db)):
    """Generate EDA report with real statistics from the dataset and auto-generate insights."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Use cached EDA if target hasn't changed
    if dataset.eda_data and not target:
        try:
            cached = json.loads(dataset.eda_data)
            cached["dataset_id"] = dataset_id
            # Ensure insights exist
            InsightService.get_insights(dataset_id, db)
            return cached
        except Exception:
            pass

    df = DatasetProfiler.load_dataset(dataset.file_path)
    effective_target = target or dataset.target_column
    eda_results = EDAEngine.run_full_eda(df, target=effective_target)
    eda_results["dataset_id"] = dataset_id

    # Cache EDA
    dataset.eda_data = json.dumps(eda_results)
    if effective_target:
        dataset.target_column = effective_target
    db.commit()

    # Generate actionable auto-insights
    try:
        InsightService.generate_insights(dataset_id, eda_results, db)
    except Exception as e:
        pass

    return eda_results


@router.get("/{dataset_id}/insights")
def get_dataset_insights(dataset_id: str, db: Session = Depends(get_db)):
    """Get all automated quality and statistical insights for a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    insights = InsightService.get_insights(dataset_id, db)
    # If no insights yet and eda_data exists, generate now
    if not insights and dataset.eda_data:
        try:
            eda_data = json.loads(dataset.eda_data)
            insights = InsightService.generate_insights(dataset_id, eda_data, db)
        except Exception:
            pass

    return {"dataset_id": dataset_id, "insights": insights, "count": len(insights)}
