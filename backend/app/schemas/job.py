from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.db.models import JobStatus, JobType


class JobCreate(BaseModel):
    job_type: JobType = JobType.TEST_JOB


class JobResponse(BaseModel):
    id: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    total: int
    items: list[JobResponse]
