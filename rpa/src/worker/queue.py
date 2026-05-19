import asyncio
import json
import logging
from datetime import datetime, timezone

from db.connection import get_session, init_db, reset_engine
from db.models import SyncLog
from schemas import SyncRequest
from state import sync_state
from utils.logger import trace_var
from worker.job_runner import _run_single_job

logger = logging.getLogger("rpa.worker.queue")


def _get_queued_jobs(session) -> list:
    """Get all queued jobs ordered by creation time."""
    return session.query(SyncLog).filter(SyncLog.status == "queued").order_by(SyncLog.started_at.asc()).all()


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
                logger.error(f"Failed to reconstruct job request for job {job.id}: {e}", exc_info=True)
                job.status = "failed"
                job.notes = f"Invalid job data: {e}"
                job.finished_at = datetime.now(timezone.utc)
                session.commit()
                session.close()
                continue

            session.close()

            # Bind the request's Trace ID so all logged actions down the line (Playwright, API, repo) are correlated
            job_trace_id = req_data.get("trace_id", f"job-{job.id}")
            token = trace_var.set(job_trace_id)

            # Process the job with a robust try-except to prevent worker crash
            try:
                logger.info(f"🚀 Starting background execution of job {job.id} for survey '{req.survey_name}'...")
                await _run_single_job(job, req)
                logger.info(f"✅ Finished background execution of job {job.id}.")
            except Exception as e:
                logger.error(f"❌ Worker critical error processing job {job.id}: {e}", exc_info=True)
                # Ensure the job is marked as failed in DB
                try:
                    db_session = get_session()
                    db_job = db_session.query(SyncLog).get(job.id)
                    if db_job and db_job.status in ["queued", "running"]:
                        db_job.status = "failed"
                        db_job.notes = f"Critical worker error: {e!s}"
                        db_job.finished_at = datetime.now(timezone.utc)
                        db_session.commit()
                    db_session.close()
                except Exception as db_err:
                    logger.error(f"⚠️ Failed to update job status on worker crash: {db_err}", exc_info=True)
            finally:
                # Reset trace_id to ensure clean context transition
                trace_var.reset(token)

            # Small delay between jobs
            await asyncio.sleep(2)

    finally:
        _worker_running = False
        sync_state.queue_count = 0


async def trigger_worker():
    """Trigger the queue worker if it's not already running."""
    if not _worker_running:
        asyncio.create_task(_queue_worker())
