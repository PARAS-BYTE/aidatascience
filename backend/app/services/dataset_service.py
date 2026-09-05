import os
import re
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import Dataset, UploadStatus


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename to avoid invalid path characters."""
    clean_name = os.path.basename(filename)
    clean_name = re.sub(r"[^\w\s\.-]", "", clean_name).strip()
    return clean_name or "file"


class DatasetService:
    @staticmethod
    def validate_file(file: UploadFile) -> str:
        """Validates extension and file presence."""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty.",
            )

        filename = sanitize_filename(file.filename)
        ext = filename.split(".")[-1].lower() if "." in filename else ""

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            )

        return ext

    @staticmethod
    async def save_dataset(db: Session, file: UploadFile) -> Dataset:
        """Saves uploaded file to disk and records metadata in database."""
        ext = DatasetService.validate_file(file)

        # Read file contents and check size limit
        content = await file.read()
        file_size = len(content)

        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed limit of {max_mb} MB.",
            )

        # Generate unique stored filename
        unique_id = str(uuid.uuid4())
        stored_filename = f"{unique_id}.{ext}"
        
        # Path traversal prevention
        target_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, stored_filename))
        upload_dir_abs = os.path.abspath(settings.UPLOAD_DIR)
        
        if not target_path.startswith(upload_dir_abs):
            logger.warning(f"Path traversal attempt detected: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path.",
            )

        # Save to disk
        try:
            with open(target_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write file to disk: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file to storage.",
            )

        # Save record to DB
        dataset = Dataset(
            id=unique_id,
            original_filename=sanitize_filename(file.filename),
            stored_filename=stored_filename,
            file_path=target_path,
            file_size=file_size,
            file_type=ext.upper(),
            upload_status=UploadStatus.SUCCESS,
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        logger.info(f"Successfully uploaded dataset '{dataset.original_filename}' (ID: {dataset.id}, Size: {file_size} bytes)")
        return dataset

    @staticmethod
    def get_all(db: Session) -> List[Dataset]:
        """Retrieves all uploaded datasets ordered by creation time descending."""
        return db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, dataset_id: str) -> Optional[Dataset]:
        """Finds a dataset by ID."""
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()

    @staticmethod
    def get_profile(db: Session, dataset_id: str) -> dict:
        """Retrieves or calculates dataset profile metadata."""
        import json
        from app.services.profiler import DatasetProfiler

        dataset = DatasetService.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found.",
            )

        if dataset.profile_data:
            try:
                profile = json.loads(dataset.profile_data)
                profile["dataset_id"] = dataset.id
                profile["filename"] = dataset.original_filename
                return profile
            except Exception:
                pass

        # Calculate profile
        profile = DatasetProfiler.profile_dataset(
            file_path=dataset.file_path,
            dataset_id=dataset.id,
            filename=dataset.original_filename,
        )

        # Cache profile in database
        dataset.profile_data = json.dumps(profile)
        db.commit()

        return profile

    @staticmethod
    def preview_dataset(
        db: Session,
        dataset_id: str,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        sort_col: Optional[str] = None,
        sort_dir: Optional[str] = "asc",
    ) -> dict:
        """Retrieves paginated and filtered head/row preview of the dataset."""
        import numpy as np
        import pandas as pd
        from app.services.profiler import DatasetProfiler

        dataset = DatasetService.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found.",
            )

        df = DatasetProfiler.load_dataset(dataset.file_path)
        total_rows, total_cols = df.shape
        columns = [str(c) for c in df.columns]
        dtypes = {str(c): str(df[c].dtype) for c in df.columns}

        # Filtering / Search across all columns
        if search and search.strip():
            search_term = search.strip().lower()
            mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(search_term, regex=False)).any(axis=1)
            df = df[mask]

        filtered_total = len(df)

        # Sorting
        if sort_col and sort_col in df.columns:
            ascending = (sort_dir.lower() != "desc")
            df = df.sort_values(by=sort_col, ascending=ascending)

        # Pagination
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        paged_df = df.iloc[offset : offset + limit]

        # Convert to JSON-serializable records (replace NaN, Inf, etc.)
        paged_df = paged_df.replace([np.inf, -np.inf], None)
        # Convert timestamp or complex objects to strings
        records = []
        for _, row in paged_df.iterrows():
            row_dict = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    row_dict[str(col)] = None
                elif isinstance(val, (pd.Timestamp, datetime)):
                    row_dict[str(col)] = val.isoformat()
                elif isinstance(val, (np.integer, int)):
                    row_dict[str(col)] = int(val)
                elif isinstance(val, (np.floating, float)):
                    row_dict[str(col)] = float(val)
                elif isinstance(val, (np.bool_, bool)):
                    row_dict[str(col)] = bool(val)
                else:
                    row_dict[str(col)] = str(val)
            records.append(row_dict)

        return {
            "dataset_id": dataset.id,
            "filename": dataset.original_filename,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "columns": columns,
            "dtypes": dtypes,
            "rows": records,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def delete_dataset(db: Session, dataset_id: str) -> bool:
        """Deletes dataset record from database and removes stored file from disk."""
        dataset = DatasetService.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found.",
            )

        # Delete physical file if exists
        if os.path.exists(dataset.file_path):
            try:
                os.remove(dataset.file_path)
            except Exception as e:
                logger.error(f"Failed to delete file '{dataset.file_path}': {str(e)}")

        db.delete(dataset)
        db.commit()

        logger.info(f"Deleted dataset '{dataset.original_filename}' (ID: {dataset_id})")
        return True

