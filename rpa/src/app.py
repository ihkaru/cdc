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
    """On startup: clean up any stale 'running'/'queued' jobs left over from a previous crash/restart."""
    try:
        init_db()
        session = get_session()
        stale = (
            session.query(SyncLog)
            .filter(SyncLog.status.in_(["running", "queued"]))
            .all()
        )
        if stale:
            for job in stale:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.notes = "Killed by container restart"
            session.commit()
            print(f"🧹 Startup cleanup: marked {len(stale)} stale job(s) as failed.")
        session.close()
    except Exception as e:
        print(f"⚠️ Startup cleanup failed: {e}")
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
