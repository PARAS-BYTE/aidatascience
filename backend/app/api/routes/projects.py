"""Project API routes — CRUD, stats, and activity timeline."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


# ─── Schemas ──────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str


# ─── Routes ───────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    project = ProjectService.create_project(
        db, current_user.id, body.name, body.description,
    )
    return _project_response(project)


@router.get("")
def list_projects(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all projects for the authenticated user."""
    projects = ProjectService.get_projects(db, current_user.id, status=status_filter)
    return {
        "total": len(projects),
        "items": [_project_response(p) for p in projects],
    }


@router.get("/{project_id}")
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a project with summary stats."""
    stats = ProjectService.get_project_stats(db, project_id, current_user.id)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return stats


@router.put("/{project_id}")
def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update project name, description, or status."""
    project = ProjectService.update_project(
        db, project_id, current_user.id,
        name=body.name, description=body.description, status=body.status,
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return _project_response(project)


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project and all associated datasets, experiments, and models."""
    deleted = ProjectService.delete_project(db, project_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {"detail": "Project deleted successfully"}


@router.get("/{project_id}/activity")
def get_project_activity(
    project_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent activity timeline for a project."""
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectService.get_project_activity(db, project_id, current_user.id, limit=limit)


@router.get("/{project_id}/datasets")
def get_project_datasets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all datasets in a project."""
    from app.db.models import Dataset
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    datasets = db.query(Dataset).filter(
        Dataset.project_id == project_id,
        Dataset.user_id == current_user.id,
    ).order_by(Dataset.created_at.desc()).all()

    return {
        "total": len(datasets),
        "items": [
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "file_size": d.file_size,
                "file_type": d.file_type,
                "upload_status": d.upload_status.value,
                "version": d.version,
                "created_at": d.created_at.isoformat(),
            }
            for d in datasets
        ],
    }


@router.get("/{project_id}/experiments")
def get_project_experiments(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all experiments in a project."""
    import json
    from app.db.models import Experiment
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    experiments = db.query(Experiment).filter(
        Experiment.project_id == project_id,
        Experiment.user_id == current_user.id,
    ).order_by(Experiment.created_at.desc()).all()

    return {
        "total": len(experiments),
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "algorithm": e.algorithm,
                "status": e.status.value,
                "metrics": json.loads(e.metrics) if e.metrics else None,
                "created_at": e.created_at.isoformat(),
            }
            for e in experiments
        ],
    }


@router.get("/{project_id}/models")
def get_project_models(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all models in a project."""
    import json
    from app.db.models import MLModel
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    models = db.query(MLModel).filter(
        MLModel.project_id == project_id,
        MLModel.user_id == current_user.id,
    ).order_by(MLModel.created_at.desc()).all()

    return {
        "total": len(models),
        "items": [
            {
                "id": m.id,
                "name": m.name,
                "algorithm": m.algorithm,
                "status": m.status.value,
                "metrics": json.loads(m.metrics) if m.metrics else None,
                "version": m.version,
                "created_at": m.created_at.isoformat(),
            }
            for m in models
        ],
    }


def _project_response(project) -> dict:
    return {
        "id": project.id,
        "user_id": project.user_id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }
