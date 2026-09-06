"""Project management service — CRUD, stats, and activity timeline."""
import json
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    Project, Dataset, Experiment, MLModel, UserActivity,
    ExperimentStatus, ModelStatus,
)
from app.core.logging import logger


class ProjectService:
    """Encapsulates all project-related business logic."""

    # ─── CRUD ─────────────────────────────────────────────────────────

    @staticmethod
    def create_project(
        db: Session,
        user_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Project:
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Log activity
        activity = UserActivity(
            user_id=user_id,
            action="CREATE_PROJECT",
            title=f"Created project '{name}'",
            details=json.dumps({"project_id": project.id}),
        )
        db.add(activity)
        db.commit()

        logger.info(f"Created project '{name}' (ID: {project.id}) for user {user_id}")
        return project

    @staticmethod
    def get_projects(db: Session, user_id: str, status: Optional[str] = None) -> List[Project]:
        query = db.query(Project).filter(Project.user_id == user_id)
        if status:
            query = query.filter(Project.status == status)
        return query.order_by(Project.updated_at.desc()).all()

    @staticmethod
    def get_project(db: Session, project_id: str, user_id: str) -> Optional[Project]:
        return db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
        ).first()

    @staticmethod
    def update_project(
        db: Session,
        project_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Project]:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
        ).first()
        if not project:
            return None

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status

        db.commit()
        db.refresh(project)
        logger.info(f"Updated project '{project.name}' (ID: {project.id})")
        return project

    @staticmethod
    def delete_project(db: Session, project_id: str, user_id: str) -> bool:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
        ).first()
        if not project:
            return False

        db.delete(project)
        db.commit()
        logger.info(f"Deleted project '{project.name}' (ID: {project_id})")
        return True

    # ─── Stats ────────────────────────────────────────────────────────

    @staticmethod
    def get_project_stats(db: Session, project_id: str, user_id: str) -> Optional[dict]:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
        ).first()
        if not project:
            return None

        dataset_count = db.query(func.count(Dataset.id)).filter(
            Dataset.project_id == project_id,
        ).scalar()

        experiment_count = db.query(func.count(Experiment.id)).filter(
            Experiment.project_id == project_id,
        ).scalar()

        completed_experiments = db.query(func.count(Experiment.id)).filter(
            Experiment.project_id == project_id,
            Experiment.status == ExperimentStatus.COMPLETED,
        ).scalar()

        model_count = db.query(func.count(MLModel.id)).filter(
            MLModel.project_id == project_id,
        ).scalar()

        # Best model (highest metric value among completed experiments)
        best_experiment = db.query(Experiment).filter(
            Experiment.project_id == project_id,
            Experiment.status == ExperimentStatus.COMPLETED,
            Experiment.metrics.isnot(None),
        ).order_by(Experiment.created_at.desc()).first()

        best_model_info = None
        if best_experiment and best_experiment.metrics:
            try:
                metrics = json.loads(best_experiment.metrics)
                best_model_info = {
                    "algorithm": best_experiment.algorithm,
                    "metrics": metrics,
                    "experiment_id": best_experiment.id,
                }
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "project_id": project_id,
            "name": project.name,
            "status": project.status,
            "datasets": dataset_count,
            "experiments": experiment_count,
            "completed_experiments": completed_experiments,
            "models": model_count,
            "best_model": best_model_info,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }

    # ─── Activity ─────────────────────────────────────────────────────

    @staticmethod
    def get_project_activity(
        db: Session,
        project_id: str,
        user_id: str,
        limit: int = 50,
    ) -> List[dict]:
        """Get recent activity for a project by querying UserActivity for related entities."""
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
        ).first()
        if not project:
            return []

        # Get dataset IDs in this project
        dataset_ids = [d.id for d in db.query(Dataset.id).filter(Dataset.project_id == project_id).all()]

        # Get activities related to this project's datasets
        activities = db.query(UserActivity).filter(
            UserActivity.user_id == user_id,
        ).order_by(UserActivity.created_at.desc()).limit(limit * 3).all()

        # Filter to project-relevant activities
        project_activities = []
        for a in activities:
            try:
                details = json.loads(a.details) if a.details else {}
            except (json.JSONDecodeError, TypeError):
                details = {}

            # Include if the activity references this project or its datasets
            if details.get("project_id") == project_id:
                project_activities.append(a)
            elif details.get("dataset_id") in dataset_ids:
                project_activities.append(a)

            if len(project_activities) >= limit:
                break

        return [
            {
                "id": a.id,
                "action": a.action,
                "title": a.title,
                "details": a.details,
                "created_at": a.created_at.isoformat(),
            }
            for a in project_activities
        ]
