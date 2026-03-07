"""
FastAPI wrapper for RPA sync engine.
Provides HTTP API for triggering sync, checking status, and health checks.
Now with database-backed job queue for sequential processing.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add current directory (src/) to path so direct imports (e.g. `from db.connection import...`) work
sys.path.insert(0, os.path.dirname(__file__))

from db.connection import init_db, get_session, reset_engine
from db.models import SyncLog
from db.repository import SyncStats, log_sync_run, BatchUpserter

app = FastAPI(title="FASIH-SM RPA Sync API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== STATE ==========

class SyncState:
    is_running: bool = False
    current_survey: Optional[str] = None
    current_job_id: Optional[int] = None
    last_result: Optional[dict] = None
    started_at: Optional[datetime] = None
    queue_count: int = 0

sync_state = SyncState()


# ========== SCHEMAS ==========

class SyncRequest(BaseModel):
    survey_config_id: str
    survey_name: str
    sso_username: str
    sso_password: str  # Already decrypted by dashboard
    filter_provinsi: str = ""
    filter_kabupaten: str = ""
    filter_rotation: str = "pengawas"


class SyncResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[int] = None
    queue_position: Optional[int] = None


class StatusResponse(BaseModel):
    is_running: bool
    current_survey: Optional[str] = None
    current_job_id: Optional[int] = None
    started_at: Optional[str] = None
    last_result: Optional[dict] = None
    queue: list = []


# ========== QUEUE HELPERS ==========

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


# ========== SYNC ENGINE ==========

async def _run_single_job(sync_log: SyncLog, req: SyncRequest):
    """Run the actual sync cycle for one job."""
    from playwright.async_api import async_playwright
    from auth import auto_login
    from pages.survey_navigator import find_survey_id, navigate_to_data_tab
    from pages.filter_rotator import iterate_filters, get_total_entries
    from pages.assignment_page import get_all_assignments_metadata
    from pages.detail_page import fetch_assignments_concurrent
    from db.repository import get_existing_modifications_by_ids

    CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "30"))

    reset_engine()
    init_db()
    session = get_session()

    # Update log to running
    log = session.query(SyncLog).get(sync_log.id)
    log.status = "running"
    log.started_at = datetime.now(timezone.utc)
    session.commit()

    sync_state.is_running = True
    sync_state.current_survey = req.survey_name
    sync_state.current_job_id = log.id
    sync_state.started_at = datetime.now(timezone.utc)

    stats = SyncStats()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            try:
                page = await context.new_page()

                # Login
                login_ok = await auto_login(page, req.sso_username, req.sso_password)
                if not login_ok:
                    raise Exception("Login gagal")

                # Navigate to survey
                survey_id = await find_survey_id(page, req.survey_name)
                if not survey_id:
                    raise Exception(f"Survey '{req.survey_name}' tidak ditemukan")

                nav_ok = await navigate_to_data_tab(page, survey_id)
                if not nav_ok:
                    raise Exception("Gagal membuka tab Data")

                # Iterate filters and fetch using concurrent batch + batch upsert
                batch_upserter = BatchUpserter(session, batch_size=500)
                # Keep track of skipped items manually
                total_skipped = 0

                async for pengawas, pencacah in iterate_filters(
                    page,
                    provinsi=req.filter_provinsi,
                    kabupaten=req.filter_kabupaten,
                    rotation=req.filter_rotation,
                ):
                    metadata_batch = await get_all_assignments_metadata(page)
                    if not metadata_batch:
                        continue
                        
                    # Extract IDs
                    all_ids = [m["id"] for m in metadata_batch if m.get("id")]
                    if not all_ids:
                        continue
                        
                    # Bulk check existing modifications
                    existing_mods = get_existing_modifications_by_ids(session, all_ids)
                    
                    # Filter for new or updated records
                    to_fetch_links = []
                    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
                    
                    for m in metadata_batch:
                        rec_id = m.get("id")
                        remote_date = m.get("dateModified")
                        
                        if not rec_id:
                            continue
                            
                        # If record exists and dates match, skip it
                        if rec_id in existing_mods and existing_mods[rec_id] == remote_date:
                            total_skipped += 1
                            continue
                            
                        # Otherwise, needs fetch
                        to_fetch_links.append(f"{TARGET_URL}/assignment-detail/{rec_id}/2/1")
                        
                    if not to_fetch_links:
                        print(f"   ⏩ Semua {len(all_ids)} data belum berubah, skip fetch.")
                        continue

                    print(f"   ⬇️  Fetching {len(to_fetch_links)} data baru/berubah dari total {len(all_ids)}...")

                    # Concurrent batch fetch — 30 parallel requests
                    results = await fetch_assignments_concurrent(
                        context, to_fetch_links, concurrency=CONCURRENCY,
                    )

                    for data in results:
                        data["_survey_config_id"] = req.survey_config_id
                        batch_upserter.add(data)

                # Flush remaining records
                stats = batch_upserter.finish()
                # Manual add skipped stats that didn't go through upserter
                stats.total_skipped += total_skipped

            finally:
                await browser.close()

        # Update sync log → success
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.total_fetched = stats.total_fetched
        log.total_new = stats.total_new
        log.total_updated = stats.total_updated
        log.total_skipped = stats.total_skipped
        log.total_failed = stats.total_failed
        log.status = "success"
        session.commit()

        sync_state.last_result = {
            "status": "success",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "fetched": stats.total_fetched,
            "new": stats.total_new,
            "updated": stats.total_updated,
            "skipped": stats.total_skipped,
            "failed": stats.total_failed,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = str(e)
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    finally:
        sync_state.is_running = False
        sync_state.current_survey = None
        sync_state.current_job_id = None
        session.close()


# ========== QUEUE WORKER ==========

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
            import json
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


# ========== ROUTES ==========

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status", response_model=StatusResponse)
def status():
    # Get queued jobs
    queue = []
    try:
        reset_engine()
        init_db()
        session = get_session()
        queued = _get_queued_jobs(session)
        import json
        for i, job in enumerate(queued):
            try:
                req_data = json.loads(job.notes or "{}")
                survey_name = req_data.get("survey_name", "Unknown")
            except:
                survey_name = "Unknown"
            queue.append({
                "job_id": job.id,
                "survey_name": survey_name,
                "position": i + 1,
                "status": "queued",
            })
        session.close()
    except:
        pass

    return StatusResponse(
        is_running=sync_state.is_running,
        current_survey=sync_state.current_survey,
        current_job_id=sync_state.current_job_id,
        started_at=sync_state.started_at.isoformat() if sync_state.started_at else None,
        last_result=sync_state.last_result,
        queue=queue,
    )


@app.post("/sync", response_model=SyncResponse)
async def trigger_sync(req: SyncRequest, background_tasks: BackgroundTasks):
    import json

    # Check if this survey already has a queued or running job
    reset_engine()
    init_db()
    session = get_session()

    existing = (
        session.query(SyncLog)
        .filter(
            SyncLog.survey_config_id == req.survey_config_id,
            SyncLog.status.in_(["queued", "running"]),
        )
        .first()
    )

    if existing:
        pos = _get_queue_position(session, existing.id) if existing.status == "queued" else 0
        session.close()
        return SyncResponse(
            status="already_queued",
            message=f"Survey '{req.survey_name}' sudah dalam antrian"
                    + (f" (posisi {pos})" if pos else " (sedang berjalan)"),
            job_id=existing.id,
            queue_position=pos,
        )

    # Create queued job — store request data in notes as JSON
    sync_log = SyncLog(
        survey_config_id=req.survey_config_id,
        started_at=datetime.now(timezone.utc),
        status="queued",
        notes=json.dumps(req.dict()),
    )
    session.add(sync_log)
    session.commit()
    job_id = sync_log.id

    queue_pos = _get_queue_position(session, job_id)
    session.close()

    # Start worker if not already running
    background_tasks.add_task(_queue_worker)

    return SyncResponse(
        status="queued",
        message=f"Sync untuk '{req.survey_name}' ditambahkan ke antrian (posisi {queue_pos})",
        job_id=job_id,
        queue_position=queue_pos,
    )


@app.delete("/sync/{job_id}")
async def cancel_job(job_id: int):
    """Cancel a queued job."""
    reset_engine()
    init_db()
    session = get_session()

    job = session.query(SyncLog).get(job_id)
    if not job:
        session.close()
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "queued":
        session.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'")

    job.status = "cancelled"
    job.finished_at = datetime.now(timezone.utc)
    job.notes = "Cancelled by user"
    session.commit()
    session.close()

    return {"status": "cancelled", "message": f"Job {job_id} cancelled"}


@app.get("/vpn/check")
def check_vpn():
    import os
    try:
        if os.path.exists("/sys/class/net/ppp0"):
            with open("/proc/net/dev") as f:
                for line in f:
                    if "ppp0" in line:
                        return {"connected": True, "info": "Interface ppp0 is UP"}
            return {"connected": True, "info": "Interface ppp0 exists"}
        return {"connected": False, "reason": "Interface ppp0 not found"}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


class ProbeRequest(BaseModel):
    sso_username: str
    sso_password: str
    survey_name: str
    filter_provinsi: str = ""
    filter_kabupaten: str = ""


@app.post("/probe/datatable")
async def probe_datatable(req: ProbeRequest):
    """
    Probe: intercept ALL API responses during DataTable reload.
    Returns discovered endpoints + sample data for incremental sync analysis.
    """
    import json as json_mod
    from playwright.async_api import async_playwright
    from auth import auto_login
    from pages.survey_navigator import find_survey_id, navigate_to_data_tab
    from pages.filter_rotator import open_filter_sidebar, select_region_dropdown, click_filter_data
    from pages.assignment_page import inject_page_size_1000

    captured = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        try:
            page = await context.new_page()

            login_ok = await auto_login(page, req.sso_username, req.sso_password)
            if not login_ok:
                raise HTTPException(status_code=500, detail="Login gagal")

            survey_id = await find_survey_id(page, req.survey_name)
            if not survey_id:
                raise HTTPException(status_code=404, detail=f"Survey '{req.survey_name}' not found")
            await navigate_to_data_tab(page, survey_id)

            async def on_response(response):
                url = response.url
                content_type = response.headers.get("content-type", "")
                if response.status == 200 and ("json" in content_type or "/api/" in url):
                    try:
                        body = await response.json()
                        sample = {}
                        if isinstance(body, dict):
                            for k, v in body.items():
                                if isinstance(v, list) and len(v) > 0:
                                    sample[k] = {
                                        "_type": "array",
                                        "_length": len(v),
                                        "_first_item_keys": list(v[0].keys()) if isinstance(v[0], dict) else type(v[0]).__name__,
                                        "_first_item": v[0] if len(json_mod.dumps(v[0], default=str)) < 2000 else "[too large]",
                                    }
                                elif isinstance(v, dict):
                                    sample[k] = {k2: type(v2).__name__ for k2, v2 in v.items()}
                                else:
                                    sample[k] = v
                        else:
                            sample = {"_raw_type": type(body).__name__}

                        captured.append({
                            "url": url,
                            "method": response.request.method,
                            "status": response.status,
                            "sample": sample,
                        })
                    except:
                        captured.append({
                            "url": url,
                            "method": response.request.method,
                            "status": response.status,
                            "sample": "[parse error]",
                        })

            page.on("response", on_response)

            await open_filter_sidebar(page)
            await asyncio.sleep(1)

            if req.filter_provinsi:
                await select_region_dropdown(page, "ngx-select[name='region1Id']", req.filter_provinsi)
                await asyncio.sleep(2)
            if req.filter_kabupaten:
                await select_region_dropdown(page, "ngx-select[name='region2Id']", req.filter_kabupaten)
                await asyncio.sleep(2)

            await click_filter_data(page)
            await asyncio.sleep(3)

            await inject_page_size_1000(page)
            await asyncio.sleep(3)

            page.remove_listener("response", on_response)

        finally:
            await browser.close()

    return {"total_captured": len(captured), "endpoints": captured}
