from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.db.models import Job, JobStatus, JobType


class JobService:
    @staticmethod
    def create_job(
        db: Session,
        job_type: JobType,
        dataset_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        model_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Job:
        """Creates a new job with QUEUED status."""
        job = Job(
            job_type=job_type,
            status=JobStatus.QUEUED,
            user_id=user_id,
            dataset_id=dataset_id,
            experiment_id=experiment_id,
            model_id=model_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(f"Created job {job.id} of type '{job_type.value}' with status QUEUED")
        return job

    @staticmethod
    def start_job(db: Session, job_id: str) -> Optional[Job]:
        """Transitions job status to RUNNING."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        logger.info(f"Started job {job_id}")
        return job

    @staticmethod
    def complete_job(db: Session, job_id: str, result_data: Optional[str] = None) -> Optional[Job]:
        """Transitions job status to COMPLETED."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = JobStatus.COMPLETED
        job.progress = 100.0
        job.completed_at = datetime.now(timezone.utc)
        job.result_data = result_data
        db.commit()
        db.refresh(job)
        logger.info(f"Completed job {job_id}")
        return job

    @staticmethod
    def fail_job(db: Session, job_id: str, error_message: str) -> Optional[Job]:
        """Transitions job status to FAILED."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        db.commit()
        db.refresh(job)
        logger.error(f"Failed job {job_id}: {error_message}")
        return job

    @staticmethod
    def update_progress(db: Session, job_id: str, progress: float, message: str = None) -> Optional[Job]:
        """Update job progress."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.progress = progress
        if message:
            job.progress_message = message
        db.commit()
        return job

    @staticmethod
    def get_all(db: Session, user_id: Optional[str] = None) -> List[Job]:
        """Gets all jobs for user ordered by created_at descending."""
        query = db.query(Job)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        return query.order_by(Job.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, job_id: str, user_id: Optional[str] = None) -> Optional[Job]:
        """Finds a job by ID, optionally enforcing user ownership."""
        query = db.query(Job).filter(Job.id == job_id)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        return query.first()
