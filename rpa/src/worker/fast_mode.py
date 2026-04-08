import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from db.repository import get_existing_modifications_by_ids, BatchUpserterBulk, SyncStats
from state import sync_state

# Concurrency 3 aman untuk FASIH API — lebih dari itu server reset koneksi
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
    """
    Fetch metadata 1 user dengan semaphore throttling + jitter.
    Jitter mencegah thundering herd: semua coroutine bangun berbarengan
    dan langsung hammering server sekaligus.
    """
    # Jitter: 0-1s per slot untuk spread request secara alami
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


async def run_fast_sync(
    session,
    api_client: Any,
    survey_id: str,
    period_id: str,
    survey_config_id: str,
    prov_code: str,
    region_filter: Optional[str],
    region_group_id: str,
    filters_to_run: List[Dict[str, Any]]
) -> SyncStats:
    """
    Fast sync:
    - STEP 1: Fan-out concurrent per-pencacah (1 request per user, max 1000 records each)
    - STEP 2: Dedup check via bulk IN query
    - STEP 3: Bulk upsert via INSERT ... ON CONFLICT

    Kenapa per-pencacah (bukan 1 regional query)?
    - Server FASIH limit: max 1000 per page, NO page 2 tersedia
    - Per-pencacah: 31 users × 1000 = cover hingga 31,000 assignment total
    - Regional query: hanya dapat 1000 pertama dari seluruh kabupaten
    """
    users_total = len(filters_to_run)
    sem = asyncio.Semaphore(FASIH_CONCURRENCY)
    print(f"\n--- FASE 4: Fast Mode — Fan-Out per-Pencacah ({users_total} users, concurrency={FASIH_CONCURRENCY}) ---")
    print(f"   ℹ️  Server limit: 1000/request, no page 2 → total cover: up to {users_total * 1000:,} assignments")

    # --- STEP 1: Launch semua task sekaligus, proses as_completed (live progress) ---
    sync_state.progress.phase = "fetch_assignments"
    sync_state.progress.phase_label = f"⚡ Fan-out: fetching {users_total} users concurrently..."
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
        count = len(results)
        total_so_far = sum(1 for _ in all_metadata_map) + count
        sync_state.progress.phase_label = (
            f"⚡ [{done_count}/{users_total}] {f.get('label','?')}: {count} → total {len(all_metadata_map) + count}"
        )
        for m in results:
            rec_id = m.get("id")
            if rec_id:
                all_metadata_map[rec_id] = m
        status = "✅" if count > 0 else "○"
        print(f"   {status} [{done_count}/{users_total}] {f.get('label','?')}: {count} records")

    unique_metadata = list(all_metadata_map.values())
    print(f"\n   📊 Total unik setelah dedup: {len(unique_metadata)} assignments")

    if not unique_metadata:
        print("   ⚠️  Tidak ada data. Cek filter pencacah/pengawas dan koneksi VPN.")
        return SyncStats()

    # --- STEP 2: Bulk dedup check (1 IN query, bukan N individual) ---
    sync_state.progress.phase_label = f"🔍 Dedup check {len(unique_metadata)} records..."
    all_ids = [m["id"] for m in unique_metadata if m.get("id")]
    existing_mods = get_existing_modifications_by_ids(session, all_ids)

    to_upsert = []
    total_skipped = 0
    for m in unique_metadata:
        rec_id = m.get("id")
        remote_date = m.get("dateModifiedRemote")
        if rec_id in existing_mods and existing_mods[rec_id] == remote_date:
            total_skipped += 1
        else:
            to_upsert.append({
                "_id": rec_id,
                "assignment": m,
                "responses": [],
                "_survey_config_id": survey_config_id
            })

    print(f"   ⏭️  Skipped (unchanged): {total_skipped} | To upsert: {len(to_upsert)}")

    if not to_upsert:
        stats = SyncStats()
        stats.total_skipped = total_skipped
        return stats

    # --- STEP 3: Bulk upsert via INSERT ... ON CONFLICT ---
    sync_state.progress.phase_label = f"💾 Bulk upserting {len(to_upsert)} records..."
    upserter = BatchUpserterBulk(session, batch_size=2000)
    for row in to_upsert:
        upserter.add(row)

    stats = upserter.finish()
    stats.total_skipped += total_skipped
    print(f"   ✅ Fast sync selesai: fetched={stats.total_fetched}, new={stats.total_new}, updated={stats.total_updated}, skipped={stats.total_skipped}")
    return stats
