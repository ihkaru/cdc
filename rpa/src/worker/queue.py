import asyncio
import json
from datetime import datetime, timezone

from db.connection import get_session, init_db, reset_engine
from db.models import SyncLog

from state import sync_state
from schemas import SyncRequest
from worker.job_runner import _run_single_job

def _get_queued_jobs(session) -> list:
    """Get all queued jobs ordered by creation time."""
    return (
        session.query(SyncLog)
        .filter(SyncLog.status == "queued")
        .order_by(SyncLog.started_at.asc())
        .all()
    )


def _get_queue_position(session, job_id: int) -> int:
    """Get position of a job in the queue (1-indexed)."""
    queued = _get_queued_jobs(session)
    for i, job in enumerate(queued):
        if job.id == job_id:
            return i + 1
    return 0


_worker_running = False

async def _queue_worker():
    """Background worker that processes queued jobs one by one."""
    global _worker_running
    if _worker_running:
        return
    _worker_running = True

    try:
        while True:
            # Check for next queued job
            reset_engine()
            init_db()
            session = get_session()

            queued = _get_queued_jobs(session)
            sync_state.queue_count = len(queued)

            if not queued:
                session.close()
                break

            job = queued[0]
            # Reconstruct request from the job's notes (stored as JSON)
            try:
                req_data = json.loads(job.notes or "{}")
                req = SyncRequest(**req_data)
            except Exception as e:
                job.status = "failed"
                job.notes = f"Invalid job data: {e}"
                job.finished_at = datetime.now(timezone.utc)
                session.commit()
                session.close()
                continue

            session.close()

            # Process the job
            await _run_single_job(job, req)

            # Small delay between jobs
            await asyncio.sleep(2)

    finally:
        _worker_running = False
        sync_state.queue_count = 0
