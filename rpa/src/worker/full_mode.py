import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from db.repository import get_existing_modifications_by_ids, BatchUpserterBulk, SyncStats
from pages.detail_page import fetch_assignments_concurrent
from state import sync_state

FASIH_CONCURRENCY = int(os.getenv("FASIH_CONCURRENCY", "3"))


async def _fetch_one(
    api_client: Any,
    period_id: str,
    prov_code: str,
    region_filter: Optional[str],
    region_group_id: str,
    f: Dict,
    semaphore: asyncio.Semaphore,
    index: int = 0
) -> tuple[Dict, List[Dict]]:
    """Fetch metadata 1 user, throttled by semaphore + jitter."""
    jitter = random.uniform(0, min(index * 0.2, 2.0))
    await asyncio.sleep(jitter)
    async with semaphore:
        try:
            results = await api_client.get_assignments_metadata(
                period_id,
                prov_uuid=prov_code,
                kab_uuid=region_filter if region_filter != prov_code else None,
                kec_uuid=f.get("kec_uuid"),
                pengawas_id=f.get("pengawas_id"),
                pencacah_id=f.get("pencacah_id"),
                region_group_id=region_group_id
            )
            return f, results or []
        except Exception as e:
            print(f"   ⚠️ Error fetching {f.get('label', '?')}: {e}")
            return f, []


async def run_full_sync(
    session,
    api_client: Any,
    cookie_dict: Dict[str, str],
    survey_id: str,
    period_id: str,
    survey_config_id: str,
    prov_code: str,
    region_filter: Optional[str],
    region_group_id: str,
    filters_to_run: List[Dict[str, Any]],
    sync_log_id: int = None
) -> SyncStats:
    """
    Full sync: fan-out per-user untuk metadata, lalu fetch detail (responses) secara concurrent.
    Server hard-limit: 1000 records per user per request, no page 2.
    """
    DETAIL_CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "5"))
    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

    users_total = len(filters_to_run)
    sem = asyncio.Semaphore(FASIH_CONCURRENCY)
    print(f"\n--- FASE 4: Full Mode — Fan-Out per-Pencacah ({users_total} users, concurrency={FASIH_CONCURRENCY}) ---")

    # --- STEP 1: Fan-out metadata per user ---
    sync_state.progress.phase = "fetch_assignments"
    sync_state.progress.phase_label = f"⚡ Fan-out: fetching {users_total} users..."
    sync_state.progress.users_total = users_total
    sync_state.progress.users_done = 0

    all_tasks = [
        asyncio.ensure_future(
            _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, f, sem, idx)
        )
        for idx, f in enumerate(filters_to_run)
    ]

    all_metadata_map: Dict[str, Dict] = {}
    done_count = 0
    for coro in asyncio.as_completed(all_tasks):
        f, results = await coro
        done_count += 1
        sync_state.progress.users_done = done_count
        sync_state.progress.phase_label = (
            f"⚡ [{done_count}/{users_total}] {f.get('label','?')}: {len(results)} → total {len(all_metadata_map) + len(results)}"
        )
        for m in results:
            if m.get("id"):
                all_metadata_map[m["id"]] = m
        status = "✅" if results else "○"
        print(f"   {status} [{done_count}/{users_total}] {f.get('label','?')}: {len(results)} records")

    unique_metadata = list(all_metadata_map.values())
    print(f"\n   📊 Total unik: {len(unique_metadata)} assignments")

    if not unique_metadata:
        if done_count > 0:
            print("   ⚠️  WARNING: Metdata found in API slices but failed to map to 'id'.")
            print("   ⚠️  This usually means BPS changed field names (multi-survey variations).")
        return SyncStats()

    # --- STEP 2: Bulk dedup check ---
    sync_state.progress.phase_label = f"🔍 Dedup check {len(unique_metadata)} records..."
    all_ids = [m["id"] for m in unique_metadata if m.get("id")]
    existing_mods = get_existing_modifications_by_ids(session, all_ids)

    to_fetch_links = []
    total_skipped = 0
    for m in unique_metadata:
        rec_id = m.get("id")
        remote_date = m.get("dateModifiedRemote")
        if rec_id in existing_mods and existing_mods[rec_id] == remote_date:
            total_skipped += 1
        else:
            to_fetch_links.append(f"{TARGET_URL}/assignment-detail/{rec_id}/{survey_id}/1")

    print(f"   ⏭️  Skipped: {total_skipped} | To fetch detail: {len(to_fetch_links)}")

    if not to_fetch_links:
        stats = SyncStats()
        stats.total_skipped = total_skipped
        return stats

    # --- STEP 3: Concurrent detail fetch dengan live progress update ---
    sync_state.progress.phase_label = f"⬇️  Fetching {len(to_fetch_links)} detail assignments..."
    sync_state.progress.assignments_total = len(to_fetch_links)
    sync_state.progress.assignments_fetched = 0

    def on_progress(fetched_count: int, total: int, _data):
        sync_state.progress.assignments_fetched = fetched_count
        sync_state.progress.phase_label = (
            f"⬇️  Detail: {fetched_count}/{total} fetched..."
        )

    results = await fetch_assignments_concurrent(
        cookie_dict, to_fetch_links,
        concurrency=DETAIL_CONCURRENCY,
        on_progress=on_progress
    )
    sync_state.progress.assignments_fetched = len(results)

    # --- STEP 4: Bulk upsert detail results ---
    sync_state.progress.phase = "upsert"
    sync_state.progress.phase_label = f"💾 Bulk upserting {len(results)} records..."
    upserter = BatchUpserterBulk(session, batch_size=2000, sync_log_id=sync_log_id)
    for data in results:
        data["_survey_config_id"] = survey_config_id
        upserter.add(data)

    stats = upserter.finish()
    stats.total_skipped += total_skipped
    print(f"   ✅ Full sync selesai: fetched={stats.total_fetched}, new={stats.total_new}, skipped={stats.total_skipped}")
    return stats
