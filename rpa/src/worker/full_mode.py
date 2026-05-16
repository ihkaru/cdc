import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from db.repository import get_existing_modifications_by_ids_batched, BatchUpserterBulk, SyncStats, normalize_bps_date
from pages.detail_page import fetch_assignments_concurrent
from state import sync_state

FASIH_CONCURRENCY = int(os.getenv("FASIH_CONCURRENCY", "1"))
DETAIL_CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "20"))


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
                desa_uuid=f.get("desa_uuid"),
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
    region_full_code: Optional[str],
    region_group_id: str,
    filters_to_run: List[Dict[str, Any]],
    sync_log_id: int = None
) -> SyncStats:
    """
    Full sync: 
    1. Smart Metadata Fetch: Fan-out per user. Jika user > 1000 (cap), slice per-kecamatan.
    2. Streaming Detail Fetch: Fetch response detail JSON + real-time Batch Upsert.
    """
    # Concurrency is now managed via global constants for better reliability
    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

    users_total = len(filters_to_run)
    sem = asyncio.Semaphore(FASIH_CONCURRENCY)
    print(f"\n--- FASE 4: Full Mode — Smart Slicing & Streaming ({users_total} users) ---")

    # --- STEP 1: Metadata Fetch (concurrent) ---
    sync_state.progress.phase = "fetch_assignments"
    sync_state.progress.phase_label = f"⚡ Fan-out: fetching {users_total} users..."
    sync_state.progress.users_total = users_total
    sync_state.progress.users_done = 0

    # Use the pre-resolved parent full code for slicing (fallback to region_filter if missing)
    parent_full_code = region_full_code or region_filter
    if parent_full_code and len(str(parent_full_code)) > 20:
        print(f"   ⚠️ [RPA] Parent code is still a UUID: {parent_full_code}. Slicing might fail.")

    all_tasks = [
        _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, f, sem, idx)
        for idx, f in enumerate(filters_to_run)
    ]

    all_metadata_map: Dict[str, Dict] = {}
    done_count = 0
    
    async def _handle_results(f_user, results):
        nonlocal done_count
        done_count += 1
        sync_state.progress.users_done = done_count
        
        user_total_metadata = {m.get("id"): m for m in results if m.get("id")}
        
        # If capped at 1000, we must slice immediately
        if len(results) >= 1000 and parent_full_code:
            print(f"   ⚠️  [CAP] {f_user.get('label')} hit {len(results)} limit. Diving into sub-regions (Parent: {parent_full_code})...")
            sync_state.progress.phase_label = f"🔬 Slicing {f_user.get('label')}..."
            
            l3_list = await api_client.get_sub_regions(3, region_group_id, parent_full_code)
            if l3_list:
                async def _slice_l3(l3):
                    sub_f = f_user.copy()
                    sub_f["kec_uuid"] = l3.get("id")
                    sub_f["label"] = f"{f_user.get('label')} - {l3.get('name')}"
                    sync_state.progress.phase_label = f"🔬 Slicing {f_user.get('label')} -> {l3.get('name')}..."
                    _, sub_res = await _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, sub_f, sem, 0)
                    local_map = {m.get("id"): m for m in sub_res if m.get("id")}
                    
                    # Nested Slicing to Level 4 (e.g. RBM)
                    if len(sub_res) >= 1000:
                        l4_list = await api_client.get_sub_regions(4, region_group_id, l3.get("fullCode"))
                        if l4_list:
                            print(f"      ⚠️ L3 {l3.get('name')} still capped. Diving to L4...")
                            async def _slice_l4(l4):
                                sub_f4 = sub_f.copy()
                                sub_f4["desa_uuid"] = l4.get("id")
                                _, res4 = await _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, sub_f4, sem, 0)
                                return {m.get("id"): m for m in res4 if m.get("id")}
                            
                            l4_results = await asyncio.gather(*[_slice_l4(l4) for l4 in l4_list])
                            for r in l4_results: local_map.update(r)
                    return local_map

                l3_results = await asyncio.gather(*[_slice_l3(l3) for l3 in l3_list])
                for r in l3_results: user_total_metadata.update(r)

        # Merge this user's results into global map
        all_metadata_map.update(user_total_metadata)

        found_for_this_user = len(user_total_metadata)
        sync_state.progress.phase_label = (
            f"⚡ [{done_count}/{users_total}] {f_user.get('label','?')}: {found_for_this_user} → total {len(all_metadata_map)}"
        )
        status = "✅" if found_for_this_user else "○"
        print(f"   {status} [{done_count}/{users_total}] {f_user.get('label','?')}: {found_for_this_user} records")

    for coro in asyncio.as_completed(all_tasks):
        f, results = await coro
        await _handle_results(f, results)

    unique_metadata = list(all_metadata_map.values())
    total_found = len(unique_metadata)
    print(f"\n   📊 Total unik (after adaptive immediate slicing): {total_found:,} assignments")

    if not unique_metadata:
        return SyncStats()

    # --- STEP 2: Bulk dedup check ---
    sync_state.progress.phase_label = f"🔍 Dedup check {total_found:,} records..."
    all_ids = [m["id"] for m in unique_metadata if m.get("id")]
    existing_mods = get_existing_modifications_by_ids_batched(session, all_ids)

    to_fetch_links = []
    total_skipped = 0

    for m in unique_metadata:
        rec_id = m.get("id")
        api_val = m.get("dateModifiedRemote")
        db_val = existing_mods.get(rec_id)

        norm_api = normalize_bps_date(api_val)
        norm_db = normalize_bps_date(db_val)

        if rec_id in existing_mods and norm_db == norm_api and norm_db != "":
            total_skipped += 1
        else:
            to_fetch_links.append(f"{TARGET_URL}/assignment-detail/{rec_id}/{survey_id}/1")

    print(f"   ⏭️  Skipped (Delta): {total_skipped:,} | To fetch detail: {len(to_fetch_links):,}")

    if not to_fetch_links:
        stats = SyncStats()
        stats.total_skipped = total_skipped
        return stats

    # --- STEP 3 & 4: Streaming Fetch & Upsert ---
    # Inisialisasi upserter SEBELUM fetch loop agar bisa streaming commit
    sync_state.progress.phase = "streaming_sync"
    sync_state.progress.phase_label = f"🚀 Streaming fetch & upsert {len(to_fetch_links):,} records..."
    sync_state.progress.assignments_total = len(to_fetch_links)
    sync_state.progress.assignments_fetched = 0

    # Extremely small batch size for verification
    print(f"   🔍 Dedup check {total_found:,} records starting...")
    upserter = BatchUpserterBulk(session, batch_size=10, sync_log_id=sync_log_id)

    def on_progress(fetched_count: int, total: int, data_json: Optional[Dict]):
        sync_state.progress.assignments_fetched = fetched_count
        sync_state.progress.phase_label = (
            f"⬇️  Detail: {fetched_count}/{total} fetched & streamed..."
        )
        if data_json:
            data_json["_survey_config_id"] = survey_config_id
            upserter.add(data_json)

    # Menjalankan concurrent fetch, tapi upsert terjadi via callback di dalamnya
    # fetch_assignments_concurrent tidak lagi perlu return list raksasa
    await fetch_assignments_concurrent(
        cookie_dict, to_fetch_links,
        concurrency=DETAIL_CONCURRENCY,
        on_progress=on_progress
    )

    # Final commit untuk sisa batch terakhir
    stats = upserter.finish()
    stats.total_skipped += total_skipped
    
    print(f"   ✅ Full sync selesai: processed={stats.total_fetched:,}, new={stats.total_new:,}, skipped={stats.total_skipped:,}")
    return stats
