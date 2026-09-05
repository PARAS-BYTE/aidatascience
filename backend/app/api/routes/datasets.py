from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.dataset import DatasetListResponse, DatasetResponse, DatasetProfileResponse, DatasetPreviewResponse
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a new CSV or XLSX dataset."""
    return await DatasetService.save_dataset(db, file)


@router.get("", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_db)):
    """List all uploaded datasets."""
    datasets = DatasetService.get_all(db)
    return DatasetListResponse(total=len(datasets), items=datasets)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get metadata for a specific dataset."""
    dataset = DatasetService.get_by_id(db, dataset_id)
    if not dataset:
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
):
    """Get interactive head/row preview of the dataset with filtering, sorting, and pagination."""
    return DatasetService.preview_dataset(
        db=db,
        dataset_id=dataset_id,
        limit=limit,
        offset=offset,
        search=search,
        sort_col=sort_col,
        sort_dir=sort_dir,
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(dataset_id: str, db: Session = Depends(get_db)):
    """Get dataset profiling metrics (dimensions, missing data, duplicates, column classification)."""
    return DatasetService.get_profile(db, dataset_id)


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Delete a dataset record and its associated file."""
    DatasetService.delete_dataset(db, dataset_id)
    return {"message": f"Dataset '{dataset_id}' deleted successfully."}

