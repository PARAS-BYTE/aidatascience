"""Unsupervised Learning API Routes — Clustering AutoML, Anomaly Detection, PCA, and Data Augmentation."""
import os
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Dataset, DatasetVersion, User
from app.api.deps import get_current_user
from app.services.profiler import DatasetProfiler
from app.core.config import settings
from ml_engine.unsupervised.unsupervised_engine import UnsupervisedEngine

router = APIRouter(prefix="/datasets", tags=["Unsupervised Learning"])


class ClusteringRequest(BaseModel):
    features: Optional[List[str]] = None
    algorithm: str = "kmeans"
    n_clusters: Optional[int] = None
    auto_k: bool = True
    k_min: int = 2
    k_max: int = 8


class AnomalyRequest(BaseModel):
    features: Optional[List[str]] = None
    algorithm: str = "isolation_forest"
    contamination: float = 0.05


class PCARequest(BaseModel):
    features: Optional[List[str]] = None
    n_components: int = 2


class AppendColumnRequest(BaseModel):
    column_name: str
    values: List[Any]
    change_summary: Optional[str] = None


@router.post("/{dataset_id}/unsupervised/cluster")
def run_clustering(
    dataset_id: str,
    req: ClusteringRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run AutoML clustering (K-Means, DBSCAN, Agglomerative, GMM) with automated segment profiling."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    result = UnsupervisedEngine.run_clustering(
        df=df,
        feature_columns=req.features,
        algorithm=req.algorithm,
        n_clusters=req.n_clusters,
        auto_k=req.auto_k,
        k_min=req.k_min,
        k_max=req.k_max,
    )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result


@router.post("/{dataset_id}/unsupervised/anomalies")
def detect_anomalies(
    dataset_id: str,
    req: AnomalyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detect unlabeled anomalies using Isolation Forest or Local Outlier Factor."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    result = UnsupervisedEngine.detect_anomalies(
        df=df,
        feature_columns=req.features,
        algorithm=req.algorithm,
        contamination=req.contamination,
    )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result


@router.post("/{dataset_id}/unsupervised/pca")
def run_pca(
    dataset_id: str,
    req: PCARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute Principal Component Analysis (PCA) 2D/3D projections and feature loadings."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    result = UnsupervisedEngine.run_pca(
        df=df,
        feature_columns=req.features,
        n_components=req.n_components,
    )

    return result


@router.post("/{dataset_id}/unsupervised/append-labels")
def append_unsupervised_labels(
    dataset_id: str,
    req: AppendColumnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Append predicted cluster IDs or anomaly flags as a new feature and create a new dataset version."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    if len(req.values) != len(df):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Values length ({len(req.values)}) does not match dataset row count ({len(df)})."
        )

    # Sanitize column name
    col_name = req.column_name.strip().replace(" ", "_").lower()
    df[col_name] = req.values

    # Save matching original extension
    cleaned_path = os.path.join(settings.PROCESSED_DIR, f"cleaned_{dataset.stored_filename}")
    if cleaned_path.endswith('.parquet'):
        df.to_parquet(cleaned_path, index=False)
    elif cleaned_path.endswith(('.xlsx', '.xls')):
        df.to_excel(cleaned_path, index=False)
    else:
        df.to_csv(cleaned_path, index=False)

    # Increment version
    dataset.cleaned_file_path = cleaned_path
    dataset.version = (dataset.version or 1) + 1

    summary_text = req.change_summary or f"Appended unsupervised feature '{col_name}'"
    new_version = DatasetVersion(
        dataset_id=dataset.id,
        version=dataset.version,
        file_path=cleaned_path,
        file_size=os.path.getsize(cleaned_path) if os.path.exists(cleaned_path) else 0,
        row_count=df.shape[0],
        column_count=df.shape[1],
        change_summary=summary_text,
    )
    db.add(new_version)
    db.commit()

    return {
        "success": True,
        "dataset_id": dataset.id,
        "new_version": dataset.version,
        "appended_column": col_name,
        "total_columns": df.shape[1],
        "message": f"Successfully created dataset version v{dataset.version} with feature '{col_name}'",
    }
