import os
import sys
from pathlib import Path

# Self-healing path: Ensure the directory containing this file is in sys.path
# This allows 'import db', 'import routes' etc. to work regardless of the working directory.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Initialize logging as the very first step
from utils.logger import setup_logging
setup_logging()

import logging
logger = logging.getLogger("rpa.app")

from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Database and Route imports
from db.connection import init_db, get_session
from db.models import SyncLog

from routes.sync import router as sync_router
from routes.lookup import router as lookup_router

@asynccontextmanager
async def lifespan(fastapi_app):
    """On startup: clean up stale 'running' jobs and resume 'queued' ones."""
    try:
        init_db()
        
        is_vpn_auth = os.getenv("IS_VPN_AUTH", "false").lower() == "true"
        if not is_vpn_auth:
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
                logger.info(f"🧹 Startup cleanup: marked {len(stale)} stale RUNNING job(s) as failed.")
            
            # Check if we should re-trigger the worker
            queued_count = session.query(SyncLog).filter(SyncLog.status == "queued").count()
            session.close()

            if queued_count > 0:
                from worker.queue import _queue_worker
                import asyncio
                logger.info(f"🔄 Startup: Found {queued_count} queued jobs. Auto-triggering worker...")
                asyncio.create_task(_queue_worker())

            # Start Routine Sync Scheduler
            from worker.scheduler import routine_sync_loop
            import asyncio
            logger.info("🕒 Startup: Starting Routine Sync Scheduler...")
            asyncio.create_task(routine_sync_loop())

            # 4. Headless VPN Bootstrap: Fetch cookie using environment credentials
            vpn_user = os.getenv("VPN_USER")
            vpn_pass = os.getenv("VPN_PASS")
            if vpn_user and vpn_pass:
                from auth import fetch_vpn_cookie, sync_cookie_to_db, get_current_cookie, FETCH_LOCK
                async def bootstrap_vpn():
                    # Delay slightly to let the infrastructure stabilize (DB, VPN container, etc)
                    await asyncio.sleep(10)
                    
                    async with FETCH_LOCK:
                        # CHECK DB FIRST: Don't fetch if we already have a cookie
                        # This prevents redundant Playwright sessions on every RPA restart
                        existing = await get_current_cookie()
                        if existing:
                            logger.info("ℹ️ [Startup] VPN Cookie already exists in DB. Skipping auto-bootstrap.")
                            return

                        logger.info(f"🌐 [Startup] No cookie found. Auto-bootstrapping VPN for {vpn_user}...")
                        cookie = await fetch_vpn_cookie(vpn_user, vpn_pass)
                        if cookie:
                            await sync_cookie_to_db(cookie)
                            logger.info("✅ [Startup] VPN Auto-bootstrap successful.")
                        else:
                            logger.error("❌ [Startup] VPN Auto-bootstrap failed.")
                
                asyncio.create_task(bootstrap_vpn())
        else:
            logger.info("ℹ️ Running as VPN-AUTH helper. Skipping scheduler, cleanup, and bootstrap.")

    except Exception as e:
        logger.error(f"⚠️ Startup cleanup/recovery failed: {e}", exc_info=True)
    
    yield  # Server runs here
    
    # On shutdown
    from state import sync_state
    sync_state.is_shutting_down = True
    logger.info("🛑 Shutdown: Signal received. Setting is_shutting_down = True for all workers.")

app = FastAPI(title="FASIH-SM RPA Sync API", version="1.0.0", lifespan=lifespan)

from middleware.tracing import TracingMiddleware
app.add_middleware(TracingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_router)
app.include_router(lookup_router)
