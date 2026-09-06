from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.dataset import DatasetListResponse, DatasetResponse, DatasetProfileResponse, DatasetPreviewResponse
from app.services.dataset_service import DatasetService
from app.api.deps import get_current_user, get_optional_user
from app.db.models import User

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(None, description="Optional project to attach the dataset to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new CSV or XLSX dataset tagged with the authenticated user and optionally a project."""
    valid_project_id = None
    if project_id:
        from app.db.models import Project
        project = db.query(Project).filter(
            Project.id == project_id, Project.user_id == current_user.id,
        ).first()
        if project:
            valid_project_id = project.id

    dataset = await DatasetService.save_dataset(
        db, file, user_id=current_user.id, project_id=valid_project_id
    )
    return dataset


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List uploaded datasets for the current user plus sample demo datasets."""
    from app.db.models import Dataset
    sample_names = ["customer_churn.csv", "house_prices.csv"]
    
    if not current_user:
        samples = db.query(Dataset).filter(Dataset.original_filename.in_(sample_names)).all()
        return DatasetListResponse(total=len(samples), items=samples)

    user_datasets = DatasetService.get_all(db, user_id=current_user.id)
    samples = db.query(Dataset).filter(Dataset.original_filename.in_(sample_names)).all()

    seen_ids = set()
    combined = []
    for d in list(user_datasets) + list(samples):
        if d.id not in seen_ids:
            seen_ids.add(d.id)
            combined.append(d)

    if project_id:
        combined = [d for d in combined if getattr(d, 'project_id', None) == project_id]

    return DatasetListResponse(total=len(combined), items=combined)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metadata for a specific dataset owned by the current user or sample dataset."""
    dataset = DatasetService.get_by_id(db, dataset_id, user_id=current_user.id)
    if not dataset:
        from app.db.models import Dataset
        sample_ds = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.original_filename.in_(["customer_churn.csv", "house_prices.csv"])
        ).first()
        if sample_ds:
            return sample_ds
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    sort_col: Optional[str] = None,
    sort_dir: Optional[str] = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get interactive head/row preview of the dataset with filtering, sorting, and pagination."""
    return DatasetService.preview_dataset(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        search=search,
        sort_col=sort_col,
        sort_dir=sort_dir,
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dataset profiling metrics (dimensions, missing data, duplicates, column classification)."""
    return DatasetService.get_profile(db, dataset_id, user_id=current_user.id)


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dataset record and its associated file."""
    DatasetService.delete_dataset(db, dataset_id, user_id=current_user.id)
    return {"message": f"Dataset '{dataset_id}' deleted successfully."}


@router.get("/{dataset_id}/versions")
def get_dataset_versions(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get version history for a dataset."""
    from app.db.models import Dataset as DatasetModel, DatasetVersion
    dataset = db.query(DatasetModel).filter(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    versions = db.query(DatasetVersion).filter(
        DatasetVersion.dataset_id == dataset_id,
    ).order_by(DatasetVersion.version.desc()).all()

    return {
        "dataset_id": dataset_id,
        "current_version": dataset.version,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "file_size": v.file_size,
                "row_count": v.row_count,
                "column_count": v.column_count,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
    }

