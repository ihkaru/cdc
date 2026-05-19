#!/usr/bin/env python
import asyncio
import os
import sys
import time

# Add src to path
sys_path = os.path.dirname(__file__)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
    sys.path.insert(0, os.path.join(sys_path, ".."))

from api_client import FasihApiClient
from db.connection import get_session
from db.models import SurveyConfig, SystemSettings
from worker.ultimate_engine import run_ultimate_sync

SURVEY_NAME = "GC PBI 2026 [TAHAP 2] - PENDATAAN"

async def main():
    print("="*80)
    print(f"🚀 OPTIMIZED EXPERIMENT: {SURVEY_NAME}")
    print("="*80)

    db_session = get_session()
    
    # 1. Get Config
    config = db_session.query(SurveyConfig).filter(SurveyConfig.survey_name == SURVEY_NAME).first()
    if not config:
        print(f"❌ Config not found for {SURVEY_NAME}")
        return
    
    # 2. Get Primary Cookies
    sso_rec = db_session.query(SystemSettings).filter_by(key=f"sso_state_{config.sso_username}").first()
    if not sso_rec:
        sso_rec = db_session.query(SystemSettings).filter_by(key="sso_cookies").first()
    
    import json
    try:
        c_data = json.loads(sso_rec.value)
        cookies = c_data.get("cookies") if isinstance(c_data, dict) and "cookies" in c_data else c_data
        if isinstance(cookies, list):
            cookies = {c["name"]: c["value"] for c in cookies}
    except:
        print("❌ Failed to parse cookies")
        return

    # 3. Resolve Metadata
    async with FasihApiClient(cookies) as api:
        survey_id = await api.get_survey_id(SURVEY_NAME)
        period_id, role_ids, _ = await api.get_survey_period_and_roles(survey_id)
        
        prov_uuid, region_filter, kab_full_code, region_group_id = await api.get_region_metadata(
            config.filter_provinsi, config.filter_kabupaten, survey_id
        )
        
        # Parallel Metadata Fetch (NEW!)
        print("\n📂 Fetching ALL assignment headers in parallel...")
        t_meta_start = time.perf_counter()
        ids_to_fetch = await api.get_assignments_metadata(
            period_id,
            prov_uuid=prov_uuid,
            kab_uuid=region_filter if region_filter != prov_uuid else None,
            region_group_id=region_group_id
        )
        print(f"✅ Metadata Phase finished in {time.perf_counter() - t_meta_start:.2f}s")
        print(f"📊 Total Assignments found: {len(ids_to_fetch):,}")

        if not ids_to_fetch:
            print("⚠️ No assignments found.")
            return

        # 4. Run Ultimate Sync (Detail Fetch)
        # Limit to 500 for the experiment to avoid being blocked if we go too fast
        target_ids = [m['id'] for m in ids_to_fetch[:500]]
        
        print(f"\n🚀 Launching Ultimate Engine for {len(target_ids)} details...")
        t_sync_start = time.perf_counter()
        stats = await run_ultimate_sync(
            db_session,
            api,
            survey_id,
            period_id,
            str(config.id),
            target_ids
        )
        duration = time.perf_counter() - t_sync_start
        
        print("\n" + "="*80)
        print("🏁 EXPERIMENT RESULTS")
        print("="*80)
        print(f"Throughput: {stats.total_fetched / duration:.2f} records/sec")
        print(f"Total Detail Fetched: {stats.total_fetched}")
        print(f"Total Time: {duration:.2f}s")
        print("="*80)

    db_session.close()

if __name__ == "__main__":
    asyncio.run(main())
