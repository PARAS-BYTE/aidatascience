import asyncio
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.job_service import JobService


async def run_test_job(job_id: str, duration_seconds: int = 3, should_fail: bool = False):
    """
    Asynchronous job execution worker simulation for testing the job infrastructure.
    Transitions: PENDING -> RUNNING -> COMPLETED (or FAILED).
    """
    db: Session = SessionLocal()
    try:
        # 1. Start job
        JobService.start_job(db, job_id)

        # 2. Simulate background work
        await asyncio.sleep(duration_seconds)

        if should_fail:
            JobService.fail_job(db, job_id, error_message="Simulated background job failure for testing.")
        else:
            JobService.complete_job(db, job_id, result_data="./data/results/sample_result.json")
    except Exception as e:
        JobService.fail_job(db, job_id, error_message=str(e))
    finally:
        db.close()
