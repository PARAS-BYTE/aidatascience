import json
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.security import hash_password, verify_password, create_access_token
from app.core.logging import logger
from app.db.models import User, UserActivity, Dataset, MLModel, Experiment, Job
from app.schemas.auth import UserRegisterRequest, UserUpdateRequest


class AuthService:
    @staticmethod
    def get_initials(name: str) -> str:
        parts = [p.strip() for p in name.split() if p.strip()]
        if not parts:
            return "DS"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @staticmethod
    def register_user(db: Session, req: UserRegisterRequest) -> User:
        clean_email = req.email.strip().lower()
        existing = db.query(User).filter(func.lower(User.email) == clean_email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )

        user = User(
            email=clean_email,
            name=req.name.strip(),
            hashed_password=hash_password(req.password),
            role="data_scientist",
            avatar=AuthService.get_initials(req.name),
            bio=req.bio or "AI Data Scientist & Machine Learning Practitioner",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        AuthService.log_activity(
            db=db,
            user_id=user.id,
            action="ACCOUNT_CREATED",
            title="Account registered",
            details=f"Welcome to AI Data Science Platform, {user.name}!",
        )

        logger.info(f"Registered new user: {user.email} (ID: {user.id})")
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        clean_email = email.strip().lower()
        user = db.query(User).filter(func.lower(User.email) == clean_email).first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        AuthService.log_activity(
            db=db,
            user_id=user.id,
            action="USER_LOGIN",
            title="User signed in",
            details="Successful authentication session created.",
        )
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user_profile(db: Session, user_id: str, req: UserUpdateRequest) -> User:
        user = AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        
        if req.name is not None and req.name.strip():
            user.name = req.name.strip()
            if not req.avatar:
                user.avatar = AuthService.get_initials(user.name)
        if req.bio is not None:
            user.bio = req.bio.strip()
        if req.avatar is not None and req.avatar.strip():
            user.avatar = req.avatar.strip().upper()[:4]

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def log_activity(
        db: Session,
        user_id: Optional[str],
        action: str,
        title: str,
        details: Optional[str] = None,
    ) -> Optional[UserActivity]:
        """Record a timeline activity event for a user."""
        if not user_id:
            return None
        try:
            activity = UserActivity(
                user_id=user_id,
                action=action,
                title=title,
                details=details,
            )
            db.add(activity)
            db.commit()
            db.refresh(activity)
            return activity
        except Exception as e:
            logger.warning(f"Failed to log user activity ({action}): {e}")
            db.rollback()
            return None

    @staticmethod
    def ensure_default_user_and_migrate_orphans(db: Session) -> User:
        """Seed a default administrative user if none exist, and associate orphan data."""
        default_user = db.query(User).filter(func.lower(User.email) == "admin@aidatascience.local").first()
        if not default_user:
            # Check if any user exists
            first_user = db.query(User).first()
            if first_user:
                default_user = first_user
            else:
                default_user = User(
                    email="admin@aidatascience.local",
                    name="Admin Data Scientist",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                    avatar="AD",
                    bio="Primary Platform Administrator and Lead Data Scientist",
                )
                db.add(default_user)
                db.commit()
                db.refresh(default_user)
                logger.info(f"Initialized default system user: {default_user.email}")

        # Migrate unassigned datasets to default user
        orphan_datasets = db.query(Dataset).filter(Dataset.user_id.is_(None)).all()
        for ds in orphan_datasets:
            ds.user_id = default_user.id

        # Migrate unassigned jobs to default user
        orphan_jobs = db.query(Job).filter(Job.user_id.is_(None)).all()
        for job in orphan_jobs:
            job.user_id = default_user.id

        # Migrate unassigned experiments to default user
        orphan_experiments = db.query(Experiment).filter(Experiment.user_id.is_(None)).all()
        for exp in orphan_experiments:
            exp.user_id = default_user.id

        # Migrate unassigned models to default user
        orphan_models = db.query(MLModel).filter(MLModel.user_id.is_(None)).all()
        for model in orphan_models:
            model.user_id = default_user.id

        if orphan_datasets or orphan_jobs or orphan_experiments or orphan_models:
            db.commit()
            logger.info(
                f"Migrated orphan records ({len(orphan_datasets)} datasets, {len(orphan_models)} models) to user {default_user.email}"
            )

        return default_user

    @staticmethod
    def get_user_profile_summary(db: Session, user_id: str) -> Dict[str, Any]:
        """Aggregate comprehensive metrics, datasets, models, and timeline for the user."""
        user = AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Datasets
        datasets = db.query(Dataset).filter(Dataset.user_id == user_id).order_by(Dataset.created_at.desc()).all()
        total_storage = sum(d.file_size for d in datasets)

        uploaded_datasets_list = []
        for d in datasets:
            row_count = None
            col_count = None
            if d.profile_data:
                try:
                    p = json.loads(d.profile_data)
                    shape = p.get("shape", {})
                    row_count = shape.get("rows")
                    col_count = shape.get("columns")
                except Exception:
                    pass

            uploaded_datasets_list.append({
                "id": d.id,
                "original_filename": d.original_filename,
                "file_size": d.file_size,
                "file_type": d.file_type,
                "upload_status": d.upload_status,
                "rows": row_count,
                "columns": col_count,
                "created_at": d.created_at,
                "target_column": d.target_column,
                "task_type": d.task_type,
            })

        # Models
        models = db.query(MLModel).filter(MLModel.user_id == user_id).order_by(MLModel.created_at.desc()).all()
        best_accuracy = None
        trained_models_list = []
        for m in models:
            metric_val = None
            if m.metrics:
                try:
                    parsed_metrics = json.loads(m.metrics)
                    # Extract primary score (accuracy, r2, f1, rmse)
                    for k in ["accuracy", "r2", "f1", "roc_auc", "f1_weighted"]:
                        if k in parsed_metrics:
                            metric_val = float(parsed_metrics[k])
                            break
                    if metric_val is None and parsed_metrics:
                        first_key = list(parsed_metrics.keys())[0]
                        metric_val = float(parsed_metrics[first_key])
                except Exception:
                    pass

            if metric_val is not None:
                if best_accuracy is None or metric_val > best_accuracy:
                    best_accuracy = metric_val

            trained_models_list.append({
                "id": m.id,
                "name": m.name,
                "algorithm": m.algorithm,
                "task_type": m.task_type,
                "target_column": m.target_column,
                "metric_value": metric_val,
                "status": m.status,
                "created_at": m.created_at,
            })

        # Experiments & Jobs
        exp_count = db.query(Experiment).filter(Experiment.user_id == user_id).count()
        jobs_count = db.query(Job).filter(Job.user_id == user_id).count()

        # Activities
        activities = (
            db.query(UserActivity)
            .filter(UserActivity.user_id == user_id)
            .order_by(UserActivity.created_at.desc())
            .limit(40)
            .all()
        )

        return {
            "user": user,
            "stats": {
                "datasets_count": len(datasets),
                "total_storage_bytes": total_storage,
                "models_count": len(models),
                "experiments_count": exp_count,
                "jobs_count": jobs_count,
                "best_accuracy": best_accuracy,
            },
            "uploaded_datasets": uploaded_datasets_list,
            "trained_models": trained_models_list,
            "recent_activities": activities,
        }
