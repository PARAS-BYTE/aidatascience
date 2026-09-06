"""Data Quality API routes — Assessment, Leakage Detection, and Automated Remediation."""
import json
import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Dataset, DataQualityReport, DatasetVersion, User
from app.api.deps import get_current_user
from app.services.data_quality_service import DataQualityService
from app.services.profiler import DatasetProfiler
from app.core.config import settings

router = APIRouter(prefix="/datasets", tags=["Data Quality"])


class QualityAssessRequest(BaseModel):
    target_column: Optional[str] = None


class RemediationActionRequest(BaseModel):
    drop_columns: Optional[List[str]] = None
    remove_duplicates: bool = True
    impute_missing: bool = True
    standardize_fuzzy: bool = True


def _get_accessible_dataset(db: Session, dataset_id: str, current_user: User) -> Dataset:
    sample_names = ["customer_churn.csv", "house_prices.csv"]
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        (Dataset.user_id == current_user.id) | 
        (Dataset.original_filename.in_(sample_names)) |
        (current_user.role == "admin")
    ).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/data-quality")
def get_data_quality_report(
    dataset_id: str,
    target_column: Optional[str] = Query(None, description="Optional target column for leakage analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve existing data quality report or calculate on demand."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)

    report = db.query(DataQualityReport).filter(
        DataQualityReport.dataset_id == dataset_id,
    ).first()

    target = target_column or dataset.target_column

    # If no report yet, or target requested differs, compute fresh
    if not report:
        report = DataQualityService.run_assessment_for_dataset(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id,
            target_column=target,
        )

    try:
        details = json.loads(report.details) if report.details else {}
    except Exception:
        details = {}

    return {
        "dataset_id": dataset_id,
        "overall_score": report.overall_score,
        "completeness_score": report.completeness_score,
        "validity_score": report.validity_score,
        "uniqueness_score": report.uniqueness_score,
        "consistency_score": report.consistency_score,
        "leakage_score": report.leakage_score,
        "dimensions": details.get("dimensions", {}),
        "recommendations": json.loads(report.recommendations) if report.recommendations else [],
        "summary_stats": details.get("summary_stats", {}),
        "created_at": report.created_at.isoformat(),
    }


@router.post("/{dataset_id}/data-quality/assess")
def run_data_quality_assessment(
    dataset_id: str,
    body: Optional[QualityAssessRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Force re-run and persist a comprehensive data quality assessment."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)

    target = (body.target_column if body else None) or dataset.target_column

    report = DataQualityService.run_assessment_for_dataset(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id,
        target_column=target,
    )

    details = json.loads(report.details) if report.details else {}

    return {
        "dataset_id": dataset_id,
        "overall_score": report.overall_score,
        "completeness_score": report.completeness_score,
        "validity_score": report.validity_score,
        "uniqueness_score": report.uniqueness_score,
        "consistency_score": report.consistency_score,
        "leakage_score": report.leakage_score,
        "dimensions": details.get("dimensions", {}),
        "recommendations": json.loads(report.recommendations) if report.recommendations else [],
        "summary_stats": details.get("summary_stats", {}),
        "created_at": report.created_at.isoformat(),
    }


@router.post("/{dataset_id}/data-quality/remediate")
def remediate_dataset_quality(
    dataset_id: str,
    actions: RemediationActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply high-priority quality remediations and create a new dataset version."""
    dataset = _get_accessible_dataset(db, dataset_id, current_user)

    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)
    initial_shape = df.shape

    changes_applied = []

    # 1. Drop high leakage or user-specified columns
    if actions.drop_columns:
        valid_drops = [c for c in actions.drop_columns if c in df.columns]
        if valid_drops:
            df = df.drop(columns=valid_drops)
            changes_applied.append(f"Dropped columns: {', '.join(valid_drops)}")

    # 2. Remove duplicates
    if actions.remove_duplicates:
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            df = df.drop_duplicates()
            changes_applied.append(f"Removed {dup_count} duplicate row(s)")

    # 3. Impute missing
    if actions.impute_missing:
        imputed_cols = []
        for col in df.columns:
            if df[col].isna().sum() > 0:
                if df[col].dtype in ['int64', 'float64']:
                    median_val = df[col].median()
                    df[col] = df[col].fillna(median_val)
                    imputed_cols.append(col)
                else:
                    mode_val = df[col].mode()
                    fill_val = mode_val.iloc[0] if not mode_val.empty else "Missing"
                    df[col] = df[col].fillna(fill_val)
                    imputed_cols.append(col)
        if imputed_cols:
            changes_applied.append(f"Imputed missing values in: {', '.join(imputed_cols[:5])}")

    # 4. Standardize fuzzy categories
    if actions.standardize_fuzzy:
        import difflib
        fuzzy_cols_standardized = []
        for col in df.columns:
            if df[col].dtype == object or str(df[col].dtype) in ('string', 'object'):
                series = df[col].dropna()
                uniques = series.unique()
                if 2 <= len(uniques) <= 100:
                    mapping = {}
                    for i in range(len(uniques)):
                        u1 = uniques[i]
                        for j in range(i + 1, len(uniques)):
                            u2 = uniques[j]
                            if u1.lower() == u2.lower() or (len(u1) > 3 and len(u2) > 3 and difflib.SequenceMatcher(None, u1.lower(), u2.lower()).ratio() >= 0.88):
                                canonical = u1 if len(u1) >= len(u2) else u2
                                mapping[u1] = canonical
                                mapping[u2] = canonical
                    if mapping:
                        df[col] = df[col].replace(mapping)
                        fuzzy_cols_standardized.append(col)
        if fuzzy_cols_standardized:
            changes_applied.append(f"Standardized fuzzy categories in {len(fuzzy_cols_standardized)} column(s)")

    # Save cleaned file matching format
    cleaned_path = os.path.join(settings.PROCESSED_DIR, f"cleaned_{dataset.stored_filename}")
    if cleaned_path.endswith('.parquet'):
        df.to_parquet(cleaned_path, index=False)
    elif cleaned_path.endswith(('.xlsx', '.xls')):
        df.to_excel(cleaned_path, index=False)
    else:
        df.to_csv(cleaned_path, index=False)
    final_shape = df.shape

    # Bump version
    dataset.cleaned_file_path = cleaned_path
    dataset.version = (dataset.version or 1) + 1

    summary_str = "; ".join(changes_applied) if changes_applied else "Quality remediation applied"
    new_version = DatasetVersion(
        dataset_id=dataset.id,
        version=dataset.version,
        file_path=cleaned_path,
        file_size=os.path.getsize(cleaned_path) if os.path.exists(cleaned_path) else 0,
        row_count=final_shape[0],
        column_count=final_shape[1],
        change_summary=summary_str,
    )
    db.add(new_version)
    db.commit()

    # Re-run assessment on new cleaned dataset
    new_report = DataQualityService.run_assessment_for_dataset(
        db=db,
        dataset_id=dataset.id,
        user_id=current_user.id,
        target_column=dataset.target_column,
    )

    return {
        "success": True,
        "dataset_id": dataset.id,
        "new_version": dataset.version,
        "initial_shape": initial_shape,
        "final_shape": final_shape,
        "changes_applied": changes_applied,
        "new_overall_score": new_report.overall_score,
    }
