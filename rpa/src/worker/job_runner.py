import asyncio
import os
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from api_client import FasihApiClient, FasihAuthError
from auth import auto_login, launch_stealth_browser, new_stealth_context
from connectivity import FasihConnectionError, ensure_connected
from db.connection import get_session, init_db, reset_engine
from db.models import Assignment, SyncLog, SystemSettings
from db.repository import SyncStats
from schemas import SyncRequest
from state import sync_state
from worker.fast_mode import run_fast_sync
from worker.full_mode import run_full_sync


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
    sync_state.current_survey_config_id = req.survey_config_id
    sync_state.current_job_id = log.id
    sync_state.started_at = datetime.now(timezone.utc)
    sync_state.progress.reset()

    stats = SyncStats()

    try:
        # Global timeout to prevent infinite hang (e.g. DNS or asyncio deadlock)
        async with asyncio.timeout(1200):  # 20 minutes
            async with async_playwright() as p:
                browser = await launch_stealth_browser(p)
                context = await new_stealth_context(browser, viewport={"width": 1280, "height": 800})

                try:
                    page = await context.new_page()

                    # Login
                    _progress("login", "🔐 Login SSO BPS via Playwright...")
                    login_ok, cookie_dict, err_msg = await auto_login(page, req.sso_username, req.sso_password)
                    if not login_ok:
                        raise Exception(f"Login gagal: {err_msg}")

                    # Close browser right after login!
                    await browser.close()
                    browser = None  # To avoid closing twice in finally

                    # Save cookies to DB for self-healing archiver (Multi-survey support)
                    try:
                        import json

                        db_session = get_session()
                        setting = db_session.query(SystemSettings).filter_by(key="sso_cookies").first()
                        if setting:
                            setting.value = json.dumps(cookie_dict)
                            setting.updated_at = datetime.now(timezone.utc)
                        else:
                            setting = SystemSettings(key="sso_cookies", value=json.dumps(cookie_dict))
                            db_session.add(setting)
                        db_session.commit()
                        db_session.close()
                        print("   💾 SSO cookies saved to DB (Ready for multi-survey self-healing).")
                    except Exception as db_e:
                        print(f"   ⚠️ Warning: Failed to save SSO cookies to DB: {db_e}")

                    async with FasihApiClient(cookie_dict) as api:
                        print("\n--- FASE 2: Resolving API Metadata ---")
                        _progress("resolve_survey", f"🔍 Mencari survey: {req.survey_name}...")
                        survey_id = await api.get_survey_id(req.survey_name)
                        if not survey_id:
                            raise Exception(f"Survey '{req.survey_name}' tidak ditemukan")

                        _progress("resolve_survey", "📅 Mengambil periode dan role...")
                        period_id, role_ids, survey_role_group_id = await api.get_survey_period_and_roles(survey_id)
                        if not period_id or not role_ids:
                            raise Exception(f"Period/Role tidak ditemukan untuk survey {survey_id}")

                        _progress("resolve_survey", "🗺️ Mengambil metadata region...")
                        prov_uuid, region_filter, kab_full_code, region_group_id = await api.get_region_metadata(
                            req.filter_provinsi, req.filter_kabupaten, survey_id
                        )

                        # Safety Gate: Jika provinsi diisi tapi tidak ketemu di API, jangan lanjut.
                        # Ini mencegah robot menarik data se-Indonesia/se-Provinsi secara tidak sengaja yang memicu timeout.
                        if req.filter_provinsi and not prov_uuid:
                            raise Exception(
                                f"Gagal memetakan wilayah: '{req.filter_provinsi}' tidak ditemukan di API FASIH"
                            )

                        if req.filter_kabupaten and not kab_full_code:
                            print(
                                f"   ⚠️ Warning: Kabupaten '{req.filter_kabupaten}' tidak ter-resolve, fallback ke Provinsi"
                            )

                        # --- MODE: USER SLICING (DIRECT) ---
                        # Looping langsung per Petugas (Pencacah/Pengawas).
                        # Strategi ini lebih cepat karena jumlah switch filter lebih sedikit.

                        filters_to_run = []

                        _progress("fetch_users", "👥 Mengambil daftar petugas...")
                        pengawas_list, pencacah_list = await api.get_users_by_region(
                            period_id, role_ids, kab_full_code, survey_role_group_id
                        )

                        if req.filter_rotation == "pencacah" and pencacah_list:
                            for idx, user in enumerate(pencacah_list):
                                filters_to_run.append(
                                    {
                                        "label": f"[{idx + 1}/{len(pencacah_list)}] Pencacah: {user['fullname']}",
                                        "pengawas_id": None,
                                        "pencacah_id": user["userId"],
                                    }
                                )
                            for idx, user in enumerate(pengawas_list):
                                filters_to_run.append(
                                    {
                                        "label": f"[{len(pencacah_list) + idx + 1}/{len(pencacah_list) + len(pengawas_list)}] Pengawas: {user['fullname']}",
                                        "pencacah_id": None,
                                    }
                                )
                        else:
                            for idx, user in enumerate(pengawas_list):
                                filters_to_run.append(
                                    {
                                        "label": f"[{idx + 1}/{len(pengawas_list)}] Pengawas: {user['fullname']}",
                                        "pengawas_id": user["userId"],
                                        "pencacah_id": None,
                                    }
                                )

                        # Fallback if no users found: fetch region-wide
                        if not filters_to_run:
                            filters_to_run.append(
                                {
                                    "label": "[1/1] Wilayah Saja (Tanpa Pengawas/Pencacah)",
                                    "pengawas_id": None,
                                    "pencacah_id": None,
                                }
                            )

                        users_count = len(filters_to_run)
                        _progress(
                            "fetch_assignments",
                            f"⚡ Memulai fetch {users_count} petugas secara concurrent...",
                            users_total=users_count,
                            users_done=0,
                        )

                        if SKIP_DETAIL_FETCH:
                            # Fast sync stats
                            run_stats = await run_fast_sync(
                                session=session,
                                api_client=api,
                                survey_id=survey_id,
                                period_id=period_id,
                                survey_config_id=req.survey_config_id,
                                prov_code=prov_uuid,
                                region_filter=region_filter,
                                region_full_code=kab_full_code,
                                region_group_id=region_group_id,
                                filters_to_run=filters_to_run,
                                sync_log_id=sync_log.id,
                            )
                        else:
                            # Full sync stats (Full results are in run_stats.total_fetched)
                            run_stats = await run_full_sync(
                                session=session,
                                api_client=api,
                                cookie_dict=cookie_dict,
                                survey_id=survey_id,
                                period_id=period_id,
                                survey_config_id=req.survey_config_id,
                                prov_code=prov_uuid,
                                region_filter=region_filter,
                                region_full_code=kab_full_code,
                                region_group_id=region_group_id,
                                filters_to_run=filters_to_run,
                                sync_log_id=sync_log.id,
                            )

                        stats = run_stats

                finally:
                    if "browser" in locals() and browser:
                        await browser.close()

        # Calculate total images found in this run
        total_images_in_run = 0
        import json

        from extractors.json_logic import extract_variables_from_json

        # We find assignments updated in this survey_config during this specific sync
        # Since we don't have the full list of objects easily from BulkUpserter,
        # we query the DB for the survey_config_id and date_synced (approximate)
        # OR better: we query all assignments for this survey_config that are NOT mirrored yet
        # but belong to this sync window.

        # Simplified: Just count all un-mirrored images for this survey_config
        # to give a realistic "Remaining Work" for the archiver.
        upserted_assignments = (
            session.query(Assignment)
            .filter(Assignment.survey_config_id == req.survey_config_id, Assignment.local_image_mirrored == False)
            .all()
        )

        for a in upserted_assignments:
            data = json.loads(a.data_json)
            vars_map = extract_variables_from_json(data)
            for k, v in vars_map.items():
                if isinstance(v, str) and v.startswith("http"):
                    is_image = any(ext in v.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]) or any(
                        kw in k.lower() or kw in v.lower() for kw in ["foto", "image", "media"]
                    )
                    if is_image:
                        total_images_in_run += 1

        # Update sync log → success
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.total_fetched = stats.total_fetched
        log.total_new = stats.total_new
        log.total_updated = stats.total_updated
        log.total_skipped = stats.total_skipped
        log.total_failed = stats.total_failed
        log.total_images = total_images_in_run
        log.images_mirrored = 0  # Will be updated by archiver in background
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

    except (FasihConnectionError, FasihAuthError) as e:
        print(f"❌ Connection/Auth Failure: {e}")
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = f"Infrastructure Failure: {e!s}"
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    except TimeoutError:
        print(f"❌ Job Timeout: Sync for {req.survey_name} took longer than 20 minutes.")
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = "Killed by global timeout (20 mins)"
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": "Global timeout exceeded (20 mins)",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    except asyncio.CancelledError:
        print(f"🛑 Job Cancelled: Sync for {req.survey_name} was interrupted by system shutdown.")
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = "Interrupted by system shutdown (SIGTERM/Restart)"
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": "Interrupted by system shutdown",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        # Re-raise to allow final cleanup
        raise
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
        sync_state.current_survey_config_id = None
        sync_state.current_job_id = None
        sync_state.started_at = None
        sync_state.progress.reset()
        session.close()
