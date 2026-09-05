from fastapi import APIRouter, Depends, BackgroundTasks, Query, status
from sqlalchemy.orm import Session
from typing import List
import asyncio

from app.db.database import get_db
from app.schemas.dataset import JobResponse, JobListResponse
from app.services.job_service import JobService
from app.db.models import JobType
from app.jobs.job_runner import run_test_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)):
    """List all jobs."""
    jobs = JobService.get_all(db)
    return JobListResponse(total=len(jobs), items=jobs)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a specific job by ID."""
    from fastapi import HTTPException
    job = JobService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/test", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_test_job(
    should_fail: bool = Query(False),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Create a simulated test job."""
    job = JobService.create_job(db, job_type=JobType.TRAINING)
    
    def _runner():
        asyncio.run(run_test_job(job.id, duration_seconds=3, should_fail=should_fail))

    if background_tasks:
        background_tasks.add_task(_runner)
    return job
