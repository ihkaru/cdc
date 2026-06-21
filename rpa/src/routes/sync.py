import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from auth import fetch_vpn_cookie
from db.connection import get_session, init_db, reset_engine
from db.models import SyncLog, SystemSettings
from schemas import StatusResponse, SyncRequest, SyncResponse, VpnCookieRequest
from state import sync_state
from utils.logger import trace_var
from worker.queue import _get_queue_position, _get_queued_jobs, _queue_worker

logger = logging.getLogger("rpa.routes.sync")
router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status", response_model=StatusResponse)
def status():
    # Get queued jobs — use existing session without reset/init every call
    queue = []
    job_status = None
    try:
        session = get_session()
        queued = _get_queued_jobs(session)
        import json

        for i, job in enumerate(queued):
            try:
                req_data = json.loads(job.notes or "{}")
                survey_name = req_data.get("survey_name", "Unknown")
            except:
                survey_name = "Unknown"
            queue.append(
                {
                    "job_id": job.id,
                    "survey_name": survey_name,
                    "position": i + 1,
                    "status": "queued",
                }
            )

        if sync_state.current_job_id:
            active_job = session.query(SyncLog).get(sync_state.current_job_id)
            if active_job:
                job_status = active_job.status
        session.close()
    except:
        pass

    return StatusResponse(
        is_running=sync_state.is_running,
        is_vpn_fetching=sync_state.is_vpn_fetching,
        current_survey=sync_state.current_survey,
        current_survey_config_id=sync_state.current_survey_config_id,
        current_job_id=sync_state.current_job_id,
        started_at=sync_state.started_at.isoformat() if sync_state.started_at else None,
        last_result=sync_state.last_result,
        queue=queue,
        progress=sync_state.progress.to_dict() if sync_state.is_running else None,
        job_status=job_status,
    )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(req: SyncRequest, background_tasks: BackgroundTasks):
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
    req_dict = req.dict()
    req_dict["trace_id"] = trace_var.get()

    sync_log = SyncLog(
        survey_config_id=req.survey_config_id,
        started_at=datetime.now(timezone.utc),
        status="queued",
        notes=json.dumps(req_dict),
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


@router.delete("/sync/{job_id}")
async def cancel_job(job_id: int):
    """Cancel a queued or running job."""
    reset_engine()
    init_db()
    session = get_session()

    job = session.query(SyncLog).get(job_id)
    if not job:
        session.close()
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ["queued", "running", "stopping"]:
        session.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'")

    if job.status == "stopping":
        session.close()
        return {"status": "stopping", "message": f"Penghentian job {job_id} sedang diproses..."}

    if job.status == "queued":
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        job.notes = "Cancelled by user"
        session.commit()
        session.close()
        return {"status": "cancelled", "message": f"Job {job_id} cancelled"}

    # Handle running job
    if job.status == "running":
        if sync_state.current_job_id == job_id:
            sync_state.stop_requested = True
            job.status = "stopping"
            job.notes = "Stop requested by user"
            session.commit()
            session.close()
            return {"status": "stopping", "message": f"Penghentian job {job_id} sedang diproses..."}
        else:
            job.status = "cancelled"
            job.finished_at = datetime.now(timezone.utc)
            job.notes = "Cancelled (orphan job cleanup)"
            session.commit()
            session.close()
            return {"status": "cancelled", "message": f"Orphan job {job_id} cleaned up."}


from connectivity import check_fasih_reachable


@router.get("/vpn/check")
async def check_vpn():
    import os

    logger.info("Received VPN status check request")
    try:
        # 1. Check application-level reachability (can we reach the FASIH server?)
        reachable, reason = await check_fasih_reachable()

        # 2. Check physical interface (Informational only)
        has_tun = os.path.exists("/sys/class/net/tun0")
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        has_vpn = has_tun or has_ppp

        if reachable:
            if has_tun:
                info = "VPN Connected (via tun0)"
            elif has_ppp:
                info = "VPN Connected (via ppp0)"
            else:
                info = "VPN Connected (Transparently via Host)"
            logger.info(f"VPN check outcome: reachable - {info}")
            return {"connected": True, "info": info}

        err_msg = f"FASIH-SM unreachable: {reason} (Interface: {'tun0/ppp0 UP' if has_vpn else 'Missing'})"
        logger.warning(f"VPN check outcome: unreachable - {err_msg}")
        return {"connected": False, "reason": err_msg}

    except Exception as e:
        logger.exception("Unexpected exception occurred in /vpn/check handler")
        return {"connected": False, "reason": f"Status check error: {e!s}"}


@router.post("/vpn/auto-fetch")
async def auto_fetch_vpn(req: VpnCookieRequest):
    """Otomasi ambil VPN cookie dan simpan ke database."""
    from auth import FETCH_LOCK, get_current_cookie, sync_cookie_to_db

    if FETCH_LOCK.locked():
        logger.warning("VPN auto-fetch request rejected: Fetch lock is already held")
        return {"status": "already_fetching", "message": "Proses auto-fetch VPN sedang berjalan..."}

    if not req.sso_username or not req.sso_password:
        logger.error("❌ SSO Username or Password is empty!")
        raise HTTPException(status_code=400, detail="SSO Username and Password are required")

    async with FETCH_LOCK:
        # Check if cookie already exists (maybe another trigger finished just now)
        existing = await get_current_cookie()
        if existing:
            logger.info("VPN cookie already exists in database. Skipping duplicate fetch.")
            return {"status": "success", "message": "Cookie sudah ada di database, melewati fetch."}

        try:
            user_display = f"{req.sso_username[:3]}***" if req.sso_username else "None"
            logger.info(f"🔄 Starting auto-fetch VPN cookie for user {user_display}...")
            cookie = await fetch_vpn_cookie(req.sso_username, req.sso_password)

            if cookie:
                await sync_cookie_to_db(cookie)
                logger.info("VPN cookie successfully synchronized to database")
                return {"status": "success", "message": "VPN cookie berhasil diperbarui"}
            else:
                logger.error("SSO authentication returned empty/invalid cookie")
                raise HTTPException(status_code=400, detail="Gagal mendapatkan VPN cookie dari Keycloak SSO")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error occurred during VPN cookie fetch execution")
            raise HTTPException(status_code=500, detail=f"Fetch error: {e}")


@router.post("/sync/refresh-assignment/{assignment_id}")
async def refresh_assignment(assignment_id: str):
    """
    Refetch assignment detail from BPS and update the local database.
    Used by the archiver to heal expired 403 links.
    """
    from api_client import FasihApiClient
    from db.models import Assignment

    reset_engine()
    init_db()
    session = get_session()

    try:
        # Get SSO cookies from SystemSettings
        cookie_setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
        if not cookie_setting:
            raise HTTPException(status_code=401, detail="No active SSO session. Please trigger a sync first.")

        cookies = json.loads(cookie_setting.value)

        async with FasihApiClient(cookies) as api:
            new_data = await api.get_assignment_detail(assignment_id)
            if not new_data:
                raise HTTPException(status_code=404, detail="Failed to fetch fresh data from BPS")

            # Update the assignment in DB
            assignment = session.query(Assignment).get(assignment_id)
            if assignment:
                assignment.data_json = new_data
                session.commit()
                logger.info(f"✅ Successfully refreshed assignment {assignment_id} in DB")
                return {"status": "success", "message": f"Assignment {assignment_id} refreshed"}
            else:
                raise HTTPException(status_code=404, detail="Assignment not found in local DB")

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


from pydantic import BaseModel


class AssignmentFileNamesPayload(BaseModel):
    assignmentId: str
    fileNames: list[str]


class RefreshImageUrlsRequest(BaseModel):
    survey_period_id: str
    assignments_payload: list[AssignmentFileNamesPayload]


@router.post("/sync/refresh-image-urls")
async def refresh_image_urls(req: RefreshImageUrlsRequest):
    """
    Get fresh S3 Presigned URLs directly from BPS /presigned-url-get endpoint.
    Returns: { "s3_key_1": "https://fresh_url...", ... }
    """
    from api_client import FasihApiClient

    reset_engine()
    init_db()
    session = get_session()

    try:
        cookie_setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
        if not cookie_setting:
            raise HTTPException(status_code=401, detail="No active SSO session. Please trigger a sync first.")

        cookies = json.loads(cookie_setting.value)

        async with FasihApiClient(cookies) as api:
            payload_dicts = [item.dict() for item in req.assignments_payload]
            fresh_urls = await api.get_fresh_image_urls(req.survey_period_id, payload_dicts)
            if fresh_urls is None:
                raise HTTPException(status_code=500, detail="Failed to fetch fresh presigned URLs from BPS")

            return {"status": "success", "data": fresh_urls}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/analytics/refresh/{survey_config_id}")
async def refresh_analytics(survey_config_id: str):
    """
    Refresh totalTargetRemote and bpsProgress for the latest sync log of a survey config.
    Uses cached SSO cookies to call BPS analytic API (no region filter → full national total).
    """
    from api_client import FasihApiClient, FasihAuthError
    from db.models import SurveyConfig

    reset_engine()
    init_db()
    session = get_session()

    try:
        # Get the survey config first
        survey_config = session.query(SurveyConfig).get(survey_config_id)
        if not survey_config:
            raise HTTPException(status_code=404, detail="Survey config not found")

        # Get the latest completed/partial sync log for this survey
        latest_log = (
            session.query(SyncLog)
            .filter(
                SyncLog.survey_config_id == survey_config_id,
                SyncLog.status.in_(["success", "partial"]),
            )
            .order_by(SyncLog.id.desc())
            .first()
        )
        if not latest_log:
            raise HTTPException(status_code=404, detail="No completed sync log found for this survey")

        # Retrieve current cookies
        cookie_setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
        cookies = json.loads(cookie_setting.value) if cookie_setting else {}

        attempts = 0
        total_target_remote = 0
        bps_progress = []

        while attempts < 2:
            try:
                if not cookies:
                    raise FasihAuthError("SSO cookies not initialized")

                async with FasihApiClient(cookies) as api:
                    # Resolve period_id from BPS API using the survey config
                    bps_survey_id = survey_config.bps_survey_id
                    if not bps_survey_id:
                        bps_survey_id = await api.get_survey_id(survey_config.survey_name)
                    if not bps_survey_id:
                        raise HTTPException(status_code=404, detail="Could not resolve BPS survey ID")

                    period_id, _, _ = await api.get_survey_period_and_roles(bps_survey_id)
                    if not period_id:
                        raise HTTPException(status_code=404, detail="Could not resolve BPS period ID")

                    # Resolve region UUIDs if config filters are set
                    prov_uuid, region_filter, _, _ = await api.get_region_metadata(
                        survey_config.filter_provinsi, survey_config.filter_kabupaten, bps_survey_id
                    )

                    # If config filters are empty, try auto-resolving from SSO profile
                    target_prov_uuid = prov_uuid
                    target_kab_uuid = region_filter
                    if not survey_config.filter_provinsi:
                        sso_prov_uuid, sso_kab_uuid, _ = await api.get_sso_user_regions(period_id, bps_survey_id)
                        if sso_prov_uuid:
                            target_prov_uuid = sso_prov_uuid
                            target_kab_uuid = sso_kab_uuid

                    # Fetch total target count using the target region UUIDs
                    total_target_remote, bps_progress = await api.get_analytic_assignment_count(
                        period_id, target_prov_uuid, target_kab_uuid
                    )
                break  # Success, break loop
            except FasihAuthError as auth_err:
                attempts += 1
                if attempts >= 2:
                    raise HTTPException(
                        status_code=401, detail=f"SSO Session Expired. Re-login otomatis gagal: {auth_err}"
                    )

                logger.info(
                    f"🔑 [Refresh] SSO cookie expired/missing ({auth_err}). Memulai headless login via Playwright..."
                )
                username = survey_config.sso_username
                try:
                    from crypto import decrypt_password

                    password = decrypt_password(survey_config.sso_password_encrypted)
                except Exception as dec_e:
                    raise HTTPException(status_code=500, detail=f"Gagal dekripsi password SSO: {dec_e}")

                from playwright.async_api import async_playwright

                from auth import auto_login, launch_stealth_browser, new_stealth_context

                new_cookies = None
                try:
                    async with async_playwright() as p:
                        browser = await launch_stealth_browser(p)
                        context = await new_stealth_context(browser)
                        page = await context.new_page()
                        success, cookies_dict, err_msg = await auto_login(page, username, password)
                        if success:
                            new_cookies = cookies_dict
                        else:
                            raise Exception(err_msg or "auto_login returned False")
                        await browser.close()
                except Exception as login_e:
                    logger.error(f"❌ [Refresh] Re-login gagal: {login_e}")
                    raise HTTPException(
                        status_code=401, detail=f"SSO Session Expired. Re-login otomatis gagal: {login_e}"
                    )

                if new_cookies:
                    cookies = new_cookies
                    # Save new cookies to database
                    cookie_setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
                    if cookie_setting:
                        cookie_setting.value = json.dumps(new_cookies)
                        cookie_setting.updated_at = datetime.now(timezone.utc)
                    else:
                        cookie_setting = SystemSettings(key="sso_cookies", value=json.dumps(new_cookies))
                        session.add(cookie_setting)
                    session.commit()
                    logger.info("✅ [Refresh] SSO cookie refreshed & saved. Retrying fetch...")

        # Update all recent sync logs for this survey with the correct national total
        updated_logs = (
            session.query(SyncLog)
            .filter(
                SyncLog.survey_config_id == survey_config_id,
                SyncLog.status.in_(["success", "partial"]),
            )
            .order_by(SyncLog.id.desc())
            .limit(5)  # Update the 5 most recent logs
            .all()
        )

        for log in updated_logs:
            log.total_target_remote = total_target_remote
            log.bps_progress = bps_progress

        session.commit()
        logger.info(
            f"✅ Refreshed analytics for survey {survey_config_id}: "
            f"total={total_target_remote:,}, breakdown={len(bps_progress)} items"
        )

        return {
            "status": "success",
            "total_target_remote": total_target_remote,
            "bps_progress": bps_progress,
            "logs_updated": len(updated_logs),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error refreshing analytics")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
