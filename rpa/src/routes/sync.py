from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, timezone
import json

from db.connection import get_session, init_db, reset_engine
from db.models import SyncLog, SystemSettings

from state import sync_state
from schemas import SyncRequest, SyncResponse, StatusResponse, VpnCookieRequest
from auth import fetch_vpn_cookie
from worker.queue import _get_queued_jobs, _get_queue_position, _queue_worker

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status", response_model=StatusResponse)
def status():
    # Get queued jobs — use existing session without reset/init every call
    queue = []
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
        progress=sync_state.progress.to_dict() if sync_state.is_running else None,
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


@router.delete("/sync/{job_id}")
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


from connectivity import check_fasih_reachable, is_session_stale

@router.get("/vpn/check")
async def check_vpn():
    import os
    try:
        # 1. Check application-level reachability (can we reach the FASIH server?)
        reachable, reason = await check_fasih_reachable()
        
        # 2. Check physical interface (Informational only)
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        
        if reachable:
            info = "VPN Connected (via ppp0)" if has_ppp else "VPN Connected (Transparently via Host)"
            return {"connected": True, "info": info}
            
        return {
            "connected": False, 
            "reason": f"FASIH-SM unreachable: {reason} (Interface ppp0: {'Exist' if has_ppp else 'Missing'})"
        }
        
    except Exception as e:
        return {"connected": False, "reason": f"Status check error: {str(e)}"}



@router.post("/vpn/auto-fetch")
async def auto_fetch_vpn(req: VpnCookieRequest):
    """Otomasi ambil VPN cookie dan simpan ke database."""
    print(f"🔄 Memulai auto-fetch VPN cookie untuk user {req.sso_username}...")
    cookie = await fetch_vpn_cookie(req.sso_username, req.sso_password)
    
    if cookie:
        try:
            reset_engine()
            init_db()
            session = get_session()
            
            # Upsert
            setting = session.query(SystemSettings).filter_by(key="vpn_cookie").first()
            if setting:
                setting.value = cookie
                setting.updated_at = datetime.now(timezone.utc)
            else:
                setting = SystemSettings(key="vpn_cookie", value=cookie)
                session.add(setting)
                
            session.commit()
            session.close()
            
            return {"status": "success", "message": "VPN cookie berhasil diperbarui"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
    else:
        raise HTTPException(status_code=400, detail="Gagal mendapatkan VPN cookie dari Keycloak SSO")


@router.post("/sync/refresh-assignment/{assignment_id}")
async def refresh_assignment(assignment_id: str):
    """
    Refetch assignment detail from BPS and update the local database.
    Used by the archiver to heal expired 403 links.
    """
    from db.models import Assignment, SystemSettings
    from api_client import FasihApiClient
    
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
                print(f"   ✅ Successfully refreshed assignment {assignment_id} in DB")
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
    from db.models import SystemSettings
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
