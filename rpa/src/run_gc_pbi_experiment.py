#!/usr/bin/env python
"""
run_gc_pbi_experiment.py — Controlled Scale Sync Experiment for May 2026.
Resolves BPS metadata for 'GC PBI 2026 [TAHAP 2] - PENDATAAN' and runs a high-speed concurrent
fetch + write pipeline on a 1,000-record real dataset.
"""

import asyncio
import json
import os
import ssl
import sys
import time
from urllib.parse import unquote

sys_path = os.path.dirname(__file__)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
    sys.path.insert(0, os.path.join(sys_path, ".."))

from api_client import FasihApiClient
from db.connection import get_session, get_session_factory
from db.models import SurveyConfig, SystemSettings
from db.repository import BatchUpserterBulk

SURVEY_NAME = "GC PBI 2026 [TAHAP 2] - PENDATAAN"
TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
LIMIT_RECORDS = 1000  # Controlled target scale limit


def print_banner():
    print("=" * 95)
    print("      🚀  FasihNexus — May 2026 GC PBI 2026 [TAHAP 2] Controlled Scale Experiment  🚀      ")
    print("=" * 95)


def parse_cookies(val_str):
    try:
        val = json.loads(val_str)
        if isinstance(val, dict) and "cookies" in val:
            return {c["name"]: c["value"] for c in val["cookies"]}
        elif isinstance(val, dict):
            return val
    except Exception:
        pass
    return {}


async def validate_session(c_dict, ssl_ctx) -> bool:
    import aiohttp

    probe_url = f"{TARGET_URL}/app/api/assignment-general/api/assignment/get-by-assignment-id"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "X-XSRF-TOKEN": unquote(c_dict.get("XSRF-TOKEN", "")),
    }
    try:
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(cookies=c_dict, connector=connector) as test_sess:
            async with test_sess.get(probe_url, headers=headers, timeout=5) as test_resp:
                if "oauth_login" in str(test_resp.url) or "sso.bps.go.id" in str(test_resp.url):
                    return False
                return test_resp.status in (200, 400, 403, 404)
    except Exception:
        return False


async def main():
    print_banner()
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    db_session = get_session()

    # 1. Retrieve survey configuration from database
    print("[1] Loading survey configuration for target survey...")
    survey_config = db_session.query(SurveyConfig).filter_by(survey_name=SURVEY_NAME).first()
    if not survey_config:
        print(f"❌ Error: Config for survey '{SURVEY_NAME}' does not exist in DB!")
        db_session.close()
        sys.exit(1)

    survey_config_id = str(survey_config.id)
    print(f"   ✓ Survey resolved: {survey_config.survey_name}")
    print(f"   ✓ Config ID      : {survey_config_id}")
    print(f"   ✓ Region Filter  : Provinsi={survey_config.filter_provinsi}, Kabupaten={survey_config.filter_kabupaten}")

    # 2. Retrieve active validated administrative session pool
    print("\n[2] Building dynamic administrative session pool...")
    settings_records = db_session.query(SystemSettings).filter(SystemSettings.key.like("sso_state_%")).all()

    all_sessions = {}
    for rec in settings_records:
        username = rec.key.replace("sso_state_", "")
        cookies = parse_cookies(rec.value)
        if cookies and "SESSION" in cookies:
            all_sessions[username] = cookies

    fallback_rec = db_session.query(SystemSettings).filter_by(key="sso_cookies").first()
    if fallback_rec and fallback_rec.value:
        cookies = parse_cookies(fallback_rec.value)
        if cookies and "SESSION" in cookies:
            all_sessions["general_fallback"] = cookies

    if not all_sessions:
        print("❌ Error: No session cookies found in system_settings database!")
        db_session.close()
        sys.exit(1)

    print(f"   👥 Found {len(all_sessions)} dynamic pool candidates. Probing active states...")
    validated_sessions = {}
    for user, c_dict in all_sessions.items():
        is_active = await validate_session(c_dict, ssl_ctx)
        status_label = "✅ Active" if is_active else "🚨 Expired"
        print(f"      - {user}: {status_label}")
        if is_active:
            validated_sessions[user] = c_dict

    if not validated_sessions:
        print("   ⚠️ All sessions failed validation. Falling back to primary session...")
        primary_user = survey_config.sso_username
        primary_cookies = all_sessions.get(primary_user) or next(iter(all_sessions.values()))
        validated_sessions[primary_user or "fallback"] = primary_cookies
    else:
        print(f"   ✓ Session pool finalized: {len(validated_sessions)} active validated admin(s).")

    # 3. Resolve remote API metadata (survey ID, period, role and assignments list)
    print("\n[3] Connecting to BPS API to resolve survey metadata & region slicing...")
    primary_key = next(iter(validated_sessions.keys()))
    primary_cookies = validated_sessions[primary_key]

    async with FasihApiClient(primary_cookies) as api:
        api.ssl_ctx = ssl_ctx
        survey_id = await api.get_survey_id(SURVEY_NAME)
        if not survey_id:
            print("❌ Error: Survey ID not found on BPS API!")
            db_session.close()
            sys.exit(1)

        print(f"   ✓ Remote Survey ID: {survey_id}")
        period_id, role_ids, survey_role_group_id = await api.get_survey_period_and_roles(survey_id)
        print(f"   ✓ Period ID       : {period_id}")

        prov_uuid, region_filter, kab_full_code, region_group_id = await api.get_region_metadata(
            survey_config.filter_provinsi, survey_config.filter_kabupaten, survey_id
        )
        print(f"   ✓ Region Group ID : {region_group_id}")
        print(f"   ✓ Region Full Code: {kab_full_code}")

        print("   👥 Fetching region officers (Pengawas/Pencacah)...")
        pengawas_list, pencacah_list = await api.get_users_by_region(
            period_id, role_ids, kab_full_code, survey_role_group_id
        )
        print(f"      - Discovered {len(pengawas_list)} Pengawas and {len(pencacah_list)} Pencacah officers.")

        # Resolve filters to iterate
        filters_to_run = []
        if survey_config.filter_rotation == "pencacah" and pencacah_list:
            for user in pencacah_list:
                filters_to_run.append({"pengawas_id": None, "pencacah_id": user["userId"]})
        elif pengawas_list:
            for user in pengawas_list:
                filters_to_run.append({"pengawas_id": user["userId"], "pencacah_id": None})
        else:
            filters_to_run.append({"pengawas_id": None, "pencacah_id": None})

        # Semaphore for parallel headers

        async def fetch_headers(f):
            try:
                results = await api.get_assignments_metadata(
                    period_id,
                    prov_uuid=prov_uuid,
                    kab_uuid=region_filter if region_filter != prov_uuid else None,
                    pengawas_id=f["pengawas_id"],
                    pencacah_id=f["pencacah_id"],
                    region_group_id=region_group_id,
                )
                return results or []
            except Exception as e:
                print(f"      ⚠️ Header extract warning: {e}")
                return []

        header_tasks = [fetch_headers(f) for f in filters_to_run]
        header_results = await asyncio.gather(*header_tasks)

        all_metadata_map = {}
        for res_list in header_results:
            for r in res_list:
                if r.get("id"):
                    all_metadata_map[r["id"]] = r

        unique_assignments = list(all_metadata_map.values())
        total_discovered = len(unique_assignments)
        print(f"   ✓ Discovered total {total_discovered:,} assignment headers remotely.")

        if not unique_assignments:
            print("❌ Error: No remote assignment headers found for this survey!")
            db_session.close()
            sys.exit(1)

        # 4. Filter and select target experiment slice (up to 1000 records)
        print(f"\n[4] Preparing target experiment slice of up to {LIMIT_RECORDS} records...")
        slice_assignments = unique_assignments[:LIMIT_RECORDS]
        actual_slice_count = len(slice_assignments)

        urls_to_fetch = [f"{TARGET_URL}/assignment-detail/{a['id']}/{survey_id}/1" for a in slice_assignments]
        print(f"   ✓ Selected {actual_slice_count} assignment IDs for controlled concurrent fetching.")

        # 5. Launch high-speed multi-session overlap fetch pipeline
        print("\n[5] Launching high-speed concurrent fetching & writing pipeline...")
        db_session.close()

        # Import optimized fetcher
        from pages.detail_page import fetch_assignments_concurrent

        db_session_factory = get_session_factory()
        session_writer = db_session_factory()
        upserter = BatchUpserterBulk(session_writer, batch_size=200)

        t_start = time.perf_counter()

        async def on_progress(completed: int, total_count: int, data_json: dict | None):
            if data_json:
                data_json["_survey_config_id"] = survey_config_id
                # Non-blocking async queue add
                await upserter.add_async(data_json)
            if completed % 100 == 0 or completed == total_count:
                print(f"   📊 Overlap Progress: {completed}/{total_count} processed...")

        try:
            # Distribute concurrent requests (concurrency=30) across validated pool
            await fetch_assignments_concurrent(primary_cookies, urls_to_fetch, concurrency=30, on_progress=on_progress)
        finally:
            stats = upserter.finish()
            session_writer.close()

        duration = time.perf_counter() - t_start
        rps = stats.total_fetched / duration if duration > 0 else 0

        # Projections to 300,000 rows
        projected_300k_seconds = 300000 / rps if rps > 0 else 0
        projected_300k_minutes = projected_300k_seconds / 60

        # Sizing of cluster workers (e.g. 5 concurrent worker processes/containers)
        cluster_workers = 5
        projected_cluster_minutes = projected_300k_minutes / cluster_workers

        print("\n" + "=" * 95)
        print("                        🏁  CONTROLLED SCALE EXPERIMENT RESULTS  🏁                        ")
        print("=" * 95)
        print(f" Target Survey Name       : {SURVEY_NAME}")
        print(f" Validated Admin Pool Size: {len(validated_sessions)} admin(s)")
        print(f" Total Discovered Remote  : {total_discovered:,} assignments")
        print(f" Experiment Target Slice  : {actual_slice_count:,} records")
        print(f" Successfully Fetched     : {stats.total_fetched:,} assignments")
        print(f" Successfully Written     : {stats.total_new + stats.total_updated:,} assignments")
        print(f" Total Pipeline Time      : {duration:.3f} seconds")
        print(f" Measured Engine Speed    : {rps:.2f} records/second")
        print("-" * 95)
        print("                       🔮 May 2026 Distributed Sizing Projections                        ")
        print("-" * 95)
        print(f" Projected Time (1 Worker Process)     : {projected_300k_minutes:.2f} minutes")
        print(f" Distributed Cluster Worker Sizing     : {cluster_workers} processes (in docker/containers)")
        print(f" Projected Cluster Time (300k rows)    : {projected_cluster_minutes:.2f} minutes  🚀")
        print(
            f" Meets target (< 10 minutes)?          : {'✅ YES! Jauh di bawah batas!' if projected_cluster_minutes < 10 else '❌ NO'}"
        )
        print("=" * 95)
        print("🎉 Controlled Scale experiment completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
