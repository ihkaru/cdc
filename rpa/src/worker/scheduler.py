import asyncio
import logging
import json
from datetime import datetime, timezone
from db.connection import get_session, init_db
from db.models import SurveyConfig, SyncLog
from connectivity import check_fasih_reachable
from worker.queue import trigger_worker
from crypto import decrypt_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

async def routine_sync_loop():
    """
    Background loop that checks for surveys due for synchronization.
    Runs every 60 seconds.
    """
    print("🕒 Routine Sync Scheduler started.", flush=True)
    
    # Wait 30 seconds on startup to let VPN and system stabilize
    await asyncio.sleep(30)
    
    while True:
        try:
            print("🔍 Scheduler: Checking for surveys to sync...", flush=True)
            # Use get_session directly
            session = get_session()
            
            # Fetch all active surveys with a valid interval
            active_surveys = (
                session.query(SurveyConfig)
                .filter(SurveyConfig.is_active == True)
                .filter(SurveyConfig.interval_minutes > 0)
                .all()
            )
            
            print(f"📊 Scheduler: Found {len(active_surveys)} active surveys with routine intervals.", flush=True)
            
            if not active_surveys:
                session.close()
                await asyncio.sleep(60)
                continue
            
            # Proactive Connectivity Check & Self-Healing
            from connectivity import ensure_connected
            print("📡 Scheduler: Checking connectivity...", flush=True)
            is_connected = await ensure_connected()
            if not is_connected:
                print("⚠️ Scheduler: VPN/FASIH unreachable even after self-healing attempt. Skipping this cycle.", flush=True)
                session.close()
                await asyncio.sleep(60)
                continue

            jobs_added = 0
            
            for survey in active_surveys:
                interval = survey.interval_minutes
                
                # Step 1: Skip if there's already an active job for this survey
                active_job = session.query(SyncLog).filter(
                    SyncLog.survey_config_id == survey.id,
                    SyncLog.status.in_(["queued", "running"])
                ).first()
                
                if active_job:
                    print(f"   ⏩ Skipping {survey.survey_name}: Job already {active_job.status}", flush=True)
                    continue
                
                # Step 2: Check time elapsed since last sync
                last_job = (
                    session.query(SyncLog)
                    .filter(SyncLog.survey_config_id == survey.id)
                ).order_by(SyncLog.started_at.desc()).first()
                
                should_sync = False
                if not last_job or not last_job.started_at:
                    should_sync = True
                else:
                    last_start = last_job.started_at.replace(tzinfo=timezone.utc)
                    delta = datetime.now(timezone.utc) - last_start
                    elapsed_mins = delta.total_seconds() / 60
                    if elapsed_mins >= interval:
                        should_sync = True
                    else:
                        print(f"   ⏳ {survey.survey_name}: Not due yet ({elapsed_mins:.1f}/{interval}m)", flush=True)
                
                if should_sync:
                    print(f"🚀 Scheduler: Enqueuing routine sync for: {survey.survey_name} (Interval: {interval}m)", flush=True)
                    
                    try:
                        raw_password = decrypt_password(survey.sso_password_encrypted)
                        
                        request_payload = {
                            "survey_config_id": str(survey.id),
                            "survey_name": survey.survey_name,
                            "sso_username": survey.sso_username,
                            "sso_password": raw_password,
                            "filter_provinsi": survey.filter_provinsi or "",
                            "filter_kabupaten": survey.filter_kabupaten or "",
                            "filter_rotation": survey.filter_rotation or "pengawas",
                            "source": "Automated routine sync"
                        }
                        
                        new_log = SyncLog(
                            survey_config_id=survey.id,
                            status="queued",
                            notes=json.dumps(request_payload),
                            total_fetched=0, total_new=0, total_updated=0, total_skipped=0, total_failed=0,
                            started_at=datetime.now(timezone.utc)
                        )
                        session.add(new_log)
                        jobs_added += 1
                    except Exception as e:
                        print(f"   ❌ Scheduler: Failed to prepare job for {survey.survey_name}: {e}", flush=True)
            
            session.commit()
            session.close()
            
            if jobs_added > 0:
                print(f"✅ Scheduler: Added {jobs_added} routine job(s) to queue.", flush=True)
                await trigger_worker()
                
        except Exception as e:
            print(f"❌ Error in routine sync loop: {e}", flush=True)
            import traceback
            traceback.print_exc()
            if 'session' in locals():
                session.close()
        
        # Check every 60 seconds
        await asyncio.sleep(60)
