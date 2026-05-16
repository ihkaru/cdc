import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from db.repository import get_existing_modifications_by_ids, BatchUpserterBulk, SyncStats, normalize_bps_date
from state import sync_state

# Gunakan angka aman (5-8) agar sesi SSO tidak di-drop paksa oleh server BPS
FASIH_CONCURRENCY = int(os.getenv("FASIH_CONCURRENCY", "5"))

async def run_fast_sync(
    session,
    api_client: Any,
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
    Fast sync STEADY:
    - Safe concurrency to prevent session drop.
    - Targeted slicing for efficiency.
    - Robust error handling.
    """
    users_total = len(filters_to_run)
    sync_state.progress.users_total = users_total
    sync_state.progress.users_done = 0
    
    all_metadata_map = {}
    done_count = 0
    parent_full_code = region_full_code or region_filter
    
    sem = asyncio.Semaphore(FASIH_CONCURRENCY)
    
    async def _fetch_meta(f_user, page=1):
        payload = {
            "period_id": period_id,
            "prov_uuid": prov_code,
            "kab_uuid": region_filter if region_filter != prov_code else None,
            "kec_uuid": f_user.get("kec_uuid"),
            "desa_uuid": f_user.get("desa_uuid"),
            "pengawas_id": f_user.get("pengawas_id"),
            "pencacah_id": f_user.get("pencacah_id"),
            "region_group_id": region_group_id,
            "page_size": 1000,
            "page_number": page
        }
        async with sem:
            # Berikan jeda antar request agar tidak dianggap serangan/spike
            await asyncio.sleep(random.uniform(0.5, 1.5))
            res = await api_client.get_assignments_metadata(**payload)
            
            if res:
                total_current = len(all_metadata_map) + len(res)
                sync_state.progress.phase_label = f"🌏 Fetching: {total_current} records... (User: {f_user.get('label')})"
            return res

    async def _process_user(f_user):
        nonlocal done_count
        try:
            results = await _fetch_meta(f_user)
            if not results:
                return

            user_data = {m["id"]: m for m in results if m.get("id")}
            
            # --- TARGETED SLICING ---
            if len(results) >= 1000 and parent_full_code:
                print(f"   🔬 [CAP] {f_user.get('label')} hit 1000. Slicing...")
                
                # Coba ambil info wilayah dari data nyata
                sample = results[0]
                reg_meta = sample.get("regionMetadata") or sample.get("region", {})
                target_kec = reg_meta.get("kecId") or f_user.get("kec_uuid")
                
                if target_kec and target_kec != parent_full_code:
                    l3_list = [{"id": target_kec, "name": "Targeted Kecamatan"}]
                else:
                    l3_list = await api_client.get_sub_regions(3, region_group_id, parent_full_code)
                
                if l3_list:
                    async def _slice_l3(l3):
                        sub_f = f_user.copy()
                        sub_f["kec_uuid"] = l3.get("id")
                        sub_res = await _fetch_meta(sub_f)
                        local_map = {m["id"]: m for m in sub_res if m.get("id")}
                        
                        if len(sub_res) >= 1000:
                            # Slicing level 4 (Desa)
                            l4_list = await api_client.get_sub_regions(4, region_group_id, l3.get("fullCode"))
                            if l4_list:
                                async def _slice_l4(l4):
                                    sub_f4 = sub_f.copy()
                                    sub_f4["desa_uuid"] = l4.get("id")
                                    res4 = await _fetch_meta(sub_f4)
                                    return {m["id"]: m for m in res4 if m.get("id")}
                                
                                # Batasi concurrency level 4 agar tidak meledak
                                l4_results = []
                                for l4 in l4_list:
                                    l4_results.append(await _slice_l4(l4))
                                for r in l4_results: local_map.update(r)
                        return local_map

                    # Gunakan sequential untuk L3 di dalam user agar sesi stabil
                    for l3 in l3_list:
                        res_l3 = await _slice_l3(l3)
                        user_data.update(res_l3)
            
            all_metadata_map.update(user_data)
            
        except Exception as e:
            print(f"   ⚠️ Error processing user {f_user.get('label')}: {e}")
        finally:
            done_count += 1
            sync_state.progress.users_done = done_count

    print(f"🚀 Launching Steady Sync (Concurrency: {FASIH_CONCURRENCY}) for {users_total} users...")
    
    # Jalankan user dalam batch kecil
    BATCH_SIZE = 10
    for i in range(0, users_total, BATCH_SIZE):
        if sync_state.is_shutting_down:
            print("🛑 [FAST] Shutdown detected. Stopping fetch loop early...")
            break
            
        batch = filters_to_run[i:i+BATCH_SIZE]
        await asyncio.gather(*[_process_user(f) for f in batch])

    unique_metadata = list(all_metadata_map.values())
    total_found = len(unique_metadata)
    print(f"\n   📊 Sync Finish: {total_found:,} unique records identified.")

    if not unique_metadata:
        return SyncStats()

    # --- STEP 2: Dedup check & Bulk Upsert ---
    sync_state.progress.phase_label = f"🔍 Dedup & Upserting {len(unique_metadata):,} records..."
    all_ids = [m["id"] for m in unique_metadata]
    
    existing_mods = {}
    CHUNK = 5000
    for i in range(0, len(all_ids), CHUNK):
        if sync_state.is_shutting_down: break
        existing_mods.update(get_existing_modifications_by_ids(session, all_ids[i:i+CHUNK]))

    upserter = BatchUpserterBulk(session, batch_size=2000, sync_log_id=sync_log_id)
    try:
        total_skipped = 0
        for m in unique_metadata:
            if sync_state.is_shutting_down:
                print("🛑 [FAST] Shutdown detected during upsert. Triggering emergency flush...")
                break
                
            rec_id = m.get("id")
            remote_date = m.get("dateModifiedRemote")
            norm_api = normalize_bps_date(remote_date)
            norm_db = normalize_bps_date(existing_mods.get(rec_id))

            if rec_id in existing_mods and norm_db == norm_api and norm_db != "":
                total_skipped += 1
            else:
                upserter.add({
                    "_id": rec_id,
                    "assignment": m,
                    "responses": [],
                    "_survey_config_id": survey_config_id
                })
    except asyncio.CancelledError:
        print("🛑 [FAST] Interrupted during upsert. Emergency flushing...")
        upserter.emergency_flush()
        raise
    finally:
        stats = upserter.finish()
        stats.total_skipped += total_skipped
        
    return stats
