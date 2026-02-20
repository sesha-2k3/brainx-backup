# Queries: Job queue operations using SKIP LOCKED for reliable dequeue

from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Job, JobStatus, JobType


async def enqueue_job(
    db: AsyncSession,
    job_type: JobType,
    payload: dict,
    scheduled_for: Optional[datetime] = None,
) -> Job:
    job = Job(
        job_type=job_type,
        payload=payload,
        status=JobStatus.PENDING,
        scheduled_for=scheduled_for or datetime.utcnow(),
    )
    db.add(job)
    await db.flush()
    return job


async def dequeue_job(db: AsyncSession) -> Optional[Job]:
    """
    Atomically claim the next pending job using SKIP LOCKED.
    Returns None if no jobs are available.
    """
    result = await db.execute(
        text("""
            UPDATE jobs 
            SET status = 'processing', 
                started_at = now(), 
                attempts = attempts + 1
            WHERE id = (
                SELECT id FROM jobs 
                WHERE status = 'pending' 
                AND scheduled_for <= now()
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING id, job_type, payload, attempts, max_attempts, created_at, started_at
        """)
    )
    row = result.fetchone()
    if not row:
        return None
    
    # Fetch the full job object
    job = await db.get(Job, row.id)
    return job


async def complete_job(db: AsyncSession, job_id: str) -> Optional[Job]:
    job = await db.get(Job, job_id)
    if not job:
        return None
    
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.utcnow()
    await db.flush()
    return job


async def fail_job(
    db: AsyncSession,
    job_id: str,
    error_message: str,
) -> Optional[Job]:
    job = await db.get(Job, job_id)
    if not job:
        return None
    
    job.error_message = error_message
    
    # Check if we should retry or mark as failed
    if job.attempts < job.max_attempts:
        job.status = JobStatus.PENDING  # Will be retried
    else:
        job.status = JobStatus.FAILED
        job.completed_at = datetime.utcnow()
    
    await db.flush()
    return job


async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[Job]:
    return await db.get(Job, job_id)


async def list_failed_jobs(
    db: AsyncSession,
    limit: int = 50,
) -> list[Job]:
    result = await db.execute(
        text("""
            SELECT * FROM jobs 
            WHERE status = 'failed'
            ORDER BY completed_at DESC
            LIMIT :limit
        """),
        {"limit": limit}
    )
    job_ids = [row.id for row in result.fetchall()]
    jobs = []
    for job_id in job_ids:
        job = await db.get(Job, job_id)
        if job:
            jobs.append(job)
    return jobs


async def retry_job(db: AsyncSession, job_id: str) -> Optional[Job]:
    """Reset a failed job to pending for retry."""
    job = await db.get(Job, job_id)
    if not job:
        return None
    
    job.status = JobStatus.PENDING
    job.error_message = None
    job.attempts = 0
    job.started_at = None
    job.completed_at = None
    await db.flush()
    return job


async def get_queue_stats(db: AsyncSession) -> dict:
    """Get counts of jobs by status."""
    result = await db.execute(
        text("""
            SELECT status, COUNT(*) as count
            FROM jobs
            GROUP BY status
        """)
    )
    stats = {row.status: row.count for row in result.fetchall()}
    return stats
