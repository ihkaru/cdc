import os
from datetime import datetime, timezone
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add current directory (src/) to path so direct imports work
sys.path.insert(0, os.path.dirname(__file__))

from db.connection import init_db, get_session
from db.models import SyncLog

from routes.sync import router as sync_router
from routes.lookup import router as lookup_router

@asynccontextmanager
async def lifespan(fastapi_app):
    """On startup: clean up stale 'running' jobs and resume 'queued' ones."""
    try:
        init_db()
        session = get_session()
        # Only mark 'running' as failed. 'queued' jobs should be preserved and resumed.
        stale = (
            session.query(SyncLog)
            .filter(SyncLog.status == "running")
            .all()
        )
        if stale:
            for job in stale:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.notes = "Killed by container restart while running"
            session.commit()
            print(f"🧹 Startup cleanup: marked {len(stale)} stale RUNNING job(s) as failed.")
        
        # Check if we should re-trigger the worker
        queued_count = session.query(SyncLog).filter(SyncLog.status == "queued").count()
        session.close()

        if queued_count > 0:
            from worker.queue import _queue_worker
            import asyncio
            print(f"🔄 Startup: Found {queued_count} queued jobs. Auto-triggering worker...")
            asyncio.create_task(_queue_worker())

    except Exception as e:
        print(f"⚠️ Startup cleanup/recovery failed: {e}")
    
    yield  # Server runs here

app = FastAPI(title="FASIH-SM RPA Sync API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_router)
app.include_router(lookup_router)
