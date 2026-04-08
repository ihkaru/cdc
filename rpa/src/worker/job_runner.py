import os
from datetime import datetime, timezone
from playwright.async_api import async_playwright

from db.connection import init_db, get_session, reset_engine
from db.models import SyncLog
from db.repository import SyncStats

from state import sync_state
from schemas import SyncRequest
from auth import auto_login
from api_client import FasihApiClient
from pages.survey_navigator import find_survey_id, navigate_to_data_tab
from pages.filter_rotator import iterate_filters, get_total_entries
from pages.assignment_page import get_all_assignments_metadata

from worker.fast_mode import run_fast_sync
from worker.full_mode import run_full_sync
from connectivity import ensure_connected


def _progress(phase: str, label: str, **kwargs):
    """Update sync_state.progress with current phase info."""
    sync_state.progress.phase = phase
    sync_state.progress.phase_label = label
    for k, v in kwargs.items():
        if hasattr(sync_state.progress, k):
            setattr(sync_state.progress, k, v)
    print(f"📊 [PROGRESS] [{phase}] {label}")

async def _run_single_job(sync_log: SyncLog, req: SyncRequest):
    """Run the actual sync cycle for one job."""
    
    # Check and self-heal connectivity (VPN/Cookie)
    await ensure_connected()
    
    SKIP_DETAIL_FETCH = os.getenv("SKIP_DETAIL_FETCH", "false").lower() == "true"

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
    sync_state.progress.reset()

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
                _progress("login", "🔐 Login SSO BPS via Playwright...")
                login_ok = await auto_login(page, req.sso_username, req.sso_password)
                if not login_ok:
                    raise Exception("Login gagal")

                # Fetch cookies and close browser right after login!
                pw_cookies = await context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in pw_cookies}
                await browser.close()
                browser = None  # To avoid closing twice in finally
                
                async with FasihApiClient(cookie_dict) as api:

                    print("\n--- FASE 2: Resolving API Metadata ---")
                    _progress("resolve", f"🔍 Mencari survey: {req.survey_name}...")
                    survey_id = await api.get_survey_id(req.survey_name)
                    if not survey_id:
                        raise Exception(f"Survey '{req.survey_name}' tidak ditemukan")

                    _progress("resolve", "📅 Mengambil periode dan role...")
                    period_id, role_ids, survey_role_group_id = await api.get_survey_period_and_roles(survey_id)
                    if not period_id or not role_ids:
                        raise Exception(f"Period/Role tidak ditemukan untuk survey {survey_id}")

                    _progress("resolve", "🗺️ Mengambil metadata region...")
                    prov_uuid, region_filter, kab_full_code, region_group_id = await api.get_region_metadata(req.filter_provinsi, req.filter_kabupaten, survey_id)

                    # --- MODE: USER SLICING (DIRECT) ---
                    # Looping langsung per Petugas (Pencacah/Pengawas).
                    # Strategi ini lebih cepat karena jumlah switch filter lebih sedikit.
                    
                    filters_to_run = []

                    _progress("fetch_users", "👥 Mengambil daftar petugas...")
                    pengawas_list, pencacah_list = await api.get_users_by_region(period_id, role_ids, kab_full_code, survey_role_group_id)

                    if req.filter_rotation == "pencacah" and pencacah_list:
                        for idx, user in enumerate(pencacah_list):
                            filters_to_run.append({
                                "label": f"[{idx+1}/{len(pencacah_list)}] Pencacah: {user['fullname']}",
                                "pengawas_id": None,
                                "pencacah_id": user['userId']
                            })
                        for idx, user in enumerate(pengawas_list):
                            filters_to_run.append({
                                "label": f"[{len(pencacah_list)+idx+1}/{len(pencacah_list)+len(pengawas_list)}] Pengawas: {user['fullname']}",
                                "pengawas_id": user['userId'],
                                "pencacah_id": None
                            })
                    else:
                        for idx, user in enumerate(pengawas_list):
                            filters_to_run.append({
                                "label": f"[{idx+1}/{len(pengawas_list)}] Pengawas: {user['fullname']}",
                                "pengawas_id": user['userId'],
                                "pencacah_id": None
                            })

                    users_count = len(filters_to_run)
                    _progress("fetch_assignments", f"⚡ Memulai fetch {users_count} petugas secara concurrent...", users_total=users_count, users_done=0)

                    if SKIP_DETAIL_FETCH:
                        stats = await run_fast_sync(
                            session=session,
                            api_client=api,
                            survey_id=survey_id,
                            period_id=period_id,
                            survey_config_id=req.survey_config_id,
                            prov_code=prov_uuid,
                            region_filter=region_filter,
                            region_group_id=region_group_id,
                            filters_to_run=filters_to_run
                        )
                    else:
                        stats = await run_full_sync(
                            session=session,
                            api_client=api,
                            cookie_dict=cookie_dict,
                            survey_id=survey_id,
                            period_id=period_id,
                            survey_config_id=req.survey_config_id,
                            prov_code=prov_uuid,
                            region_filter=region_filter,
                            region_group_id=region_group_id,
                            filters_to_run=filters_to_run
                        )


            finally:
                if 'browser' in locals() and browser:
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
