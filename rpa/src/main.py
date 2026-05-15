"""
FasihNexus Sync Engine — Main Orchestrator (API First)

Fully automated robot yang:
1. Login SSO BPS otomatis via Playwright (Headless) untuk mendapatkan Cookie.
2. Menggunakan API/aiohttp murni untuk:
   a. Navigasi dan temukan ID Survey
   b. Dapatkan Region Metadata & List Pengguna (Pengawas/Pencacah)
   c. Iterate pagination Datatable Assignment (bypass limit batas baris via filter)
   d. Fetch form detail individual secara concurrent
3. Upsert ke SQLite
4. Berjalan otomatis setiap N menit

Usage:
    python src/main.py                  # Start scheduler
    python src/main.py --once           # Jalankan 1 cycle saja
    python src/main.py --test-login     # Test login saja
"""
import argparse
import asyncio
import os
import re
import sys
import time
import json
from datetime import datetime, timezone

from playwright.async_api import async_playwright

# Self-healing path: Ensure both the current directory (src) and its parent (root) are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for d in [current_dir, parent_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config.settings import Settings
from auth import auto_login, launch_stealth_browser, new_stealth_context
from api_client import FasihApiClient
from pages.detail_page import fetch_assignments_concurrent
from db.connection import init_db, get_session
from db.repository import upsert_assignment, log_sync_run, SyncStats, BatchUpserterBulk, get_existing_modifications_by_ids_batched
from connectivity import ensure_connected


async def run_sync_cycle(settings: Settings, dry_run: bool = False):
    """
    Satu siklus lengkap sinkronisasi Hybrid-Headless.
    """
    started_at = datetime.now(timezone.utc)
    stats = SyncStats()
    timings = {}
    total_start = time.perf_counter()
    
    # --- FASE 0: KONEKTIVITAS VPN ---
    print("\n--- FASE 0: Memastikan Konektivitas VPN ---")
    await ensure_connected()
    
    print("\n" + "=" * 60)
    print(f"🤖 FasihNexus Sync Engine — Cycle dimulai")
    print(f"   Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Survey: {settings.survey_name}")
    print(f"   Rotasi: {settings.filter_rotation}")
    print(f"   Dry run: {dry_run}")
    print("=" * 60)

    # --- FASE 1: SESSION VALIDATION & LOGIN ---
    print("\n--- FASE 1: Session Validation & Login ---")
    phase_start = time.perf_counter()
    cookies = {}
    
    # Try CACHED cookies first
    from db.connection import get_session
    from db.repository import get_system_setting, set_system_setting
    
    db_session = get_session()
    cache_key = f"sso_cookies_{settings.sso_username}"
    cached_json = get_system_setting(db_session, cache_key)
    db_session.close()

    if cached_json:
        try:
            print(f"   🍪 Ditemukan cached cookies untuk {settings.sso_username}. Memvalidasi...")
            temp_cookies = json.loads(cached_json)
            # Test session dengan API ringan
            api_test = FasihApiClient(temp_cookies)
            # Mencoba fetch survey ID sebagai probe
            survey_id_probe = await api_test.get_survey_id(settings.survey_name)
            await api_test.close()
            
            if survey_id_probe:
                print(f"   ⚡ Sesi CACHE valid! Melewati login browser (Playwright skipped).")
                cookies = temp_cookies
            else:
                print(f"   ⚠️ Sesi CACHE kadaluwarsa. Memerlukan login browser.")
        except Exception as e:
            print(f"   ⚠️ Gagal menggunakan cached cookies: {e}")

    # Fallback to Playwright if no valid cookies
    if not cookies:
        print("   🎭 Memulai Playwright browser untuk login SSO...")
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(
                browser,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            login_ok, cookies_dict, err_msg = await auto_login(page, settings.sso_username, settings.sso_password)
            if not login_ok or not cookies_dict:
                print("❌ Login gagal atau cookies tidak didapatkan! Cycle dibatalkan.")
                await browser.close()
                return
                
            cookies = cookies_dict
            await browser.close()
        
        # Save fresh cookies to DB
        try:
            db_session = get_session()
            set_system_setting(db_session, cache_key, json.dumps(cookies))
            db_session.close()
            print(f"   💾 Sesi baru disimpan ke cache untuk {settings.sso_username}")
        except Exception as e:
            print(f"   ⚠️ Gagal menyimpan cookies ke DB: {e}")

    timings["login"] = int((time.perf_counter() - phase_start) * 1000)

    # Inisialisasi API Client
    api = FasihApiClient(cookies)

    # --- FASE 2: RESOLVE METADATA SURVEY & REGION ---
    print("\n--- FASE 2: Resolving API Metadata ---")
    phase_start = time.perf_counter()
    survey_id = await api.get_survey_id(settings.survey_name)
    if not survey_id:
        return

    period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)
    if not period_id or not role_ids:
        return

    prov_code, region_filter, region_full_code, region_group_id = await api.get_region_metadata(settings.filter_provinsi, settings.filter_kabupaten, survey_id)
    timings["metadata"] = int((time.perf_counter() - phase_start) * 1000)
    
    # Init DB
    survey_slug = re.sub(r'[^a-z0-9]+', '_', settings.survey_name.lower()).strip('_')
    survey_data_dir = os.path.join(os.path.dirname(settings.db_path), survey_slug)
    survey_db_path = os.path.join(survey_data_dir, "sync.db")
    
    if not dry_run:
        from db.connection import reset_engine
        reset_engine()
        os.makedirs(survey_data_dir, exist_ok=True)
        survey_db_url = f"sqlite:///{survey_db_path}"
        init_db(survey_db_url)
        session = get_session(survey_db_url)
        print(f"   📂 Data dir: {survey_data_dir}/")

    # --- FASE 3: ROTASI & FETCH ASSIGNMENTS ---
    print("\n--- FASE 3: Extract Assignment Metadata ---")
    
    pengawas_list, pencacah_list = await api.get_users_by_region(
        period_id, role_ids, region_filter or region_full_code or "", role_group_id
    )
    
    # Tentukan strategi iterasi berdasarkan setelan config rotasi
    filters_to_run = []
    if settings.filter_rotation == "pencacah" and pencacah_list:
        for idx, user in enumerate(pencacah_list):
            filters_to_run.append({
                "label": f"[{idx+1}/{len(pencacah_list)}] Pencacah: {user['fullname']}",
                "pengawas_id": None,
                "pencacah_id": user['userId']
            })
    elif pengawas_list:
        for idx, user in enumerate(pengawas_list):
            filters_to_run.append({
                "label": f"[{idx+1}/{len(pengawas_list)}] Pengawas: {user['fullname']}",
                "pengawas_id": user['userId'],
                "pencacah_id": None
            })
    else:
        filters_to_run.append({
            "label": "[1/1] Wilayah Saja (Tanpa Pengawas/Pencacah)",
            "pengawas_id": None,
            "pencacah_id": None
        })

    all_metadata_map = {}
    
    async def fetch_user_metadata(f):
        print(f"🔄 {f['label']}")
        metadata = await api.get_assignments_metadata(
            period_id, 
            prov_uuid=prov_code,
            kab_uuid=region_filter if region_filter != prov_code else None,
            pengawas_id=f['pengawas_id'], 
            pencacah_id=f['pencacah_id'],
            region_group_id=region_group_id
        )
        print(f"   📊 Ditemukan {len(metadata)} entries ({f['label']}).")
        return metadata

    # Fetch all user metadata in parallel
    metadata_results = await asyncio.gather(*(fetch_user_metadata(f) for f in filters_to_run))
    for metadata in metadata_results:
        for m in metadata:
            all_metadata_map[m['id']] = m

    unique_assignments = list(all_metadata_map.values())
    print(f"\n--- FASE 4: Fetch Detailed Assignment Data ---")
    phase_start = time.perf_counter()
    print(f"   🔗 Total Assignment Unik: {len(unique_assignments)}")
    
    if dry_run:
        stats.total_fetched = len(unique_assignments)
    else:
        if unique_assignments:
            # ── DELTA SYNC: Skip detail fetch untuk records yang tidak berubah ──
            # Bandingkan dateModifiedRemote dari datatable dengan yang tersimpan di DB.
            # get_existing_modifications_by_ids_batched menggunakan chunking 10k agar
            # aman untuk 300k+ IDs tanpa membuat IN clause raksasa.
            all_ids = [m["id"] for m in unique_assignments]
            existing_dates = get_existing_modifications_by_ids_batched(session, all_ids)

            to_fetch = []
            _debug_logged = False
            for m in unique_assignments:
                rec_id = m["id"]
                remote_date = m.get("dateModifiedRemote")
                if rec_id not in existing_dates:
                    to_fetch.append(m)
                elif existing_dates[rec_id] != remote_date:
                    if not _debug_logged and existing_dates[rec_id] and remote_date:
                        print(f"   🔬 [TIMESTAMP DEBUG] DB date: {repr(existing_dates[rec_id])} vs API date: {repr(remote_date)}")
                        _debug_logged = True
                    to_fetch.append(m)
            skipped_delta = len(unique_assignments) - len(to_fetch)

            print(f"\n   🔄 Delta check: {len(to_fetch)} perlu di-fetch, "
                  f"{skipped_delta} di-skip (tidak berubah sejak sync terakhir)")

            # Jika semua sudah up-to-date, tidak perlu fetch apapun
            if not to_fetch:
                print("   ✅ Semua data sudah up-to-date — tidak ada yang perlu di-sync!")
                stats.total_skipped = len(unique_assignments)
                timings["fetch"] = 0
            else:
                urls_to_fetch = [
                    f"{os.getenv('TARGET_URL', 'https://fasih-sm.bps.go.id')}/survey-collection/assignment-detail/{m['id']}/{survey_id}"
                    for m in to_fetch
                ]

                # Fetch secara concurrent — concurrency=100 optimal untuk VPN BPS
                # (lebih tinggi berisiko 429, lebih rendah terlalu lambat)
                results = await fetch_assignments_concurrent(cookies, urls_to_fetch, concurrency=settings.fetch_concurrency)
                timings["fetch"] = int((time.perf_counter() - phase_start) * 1000)

                # Upsert
                print("\n   💾 Menyimpan ke database (Bulk)...")
                phase_start = time.perf_counter()

                upserter = BatchUpserterBulk(session, batch_size=2000)
                for i, data in enumerate(results):
                    data["_survey_config_id"] = getattr(settings, "id", "default")
                    upserter.add(data)

                stats = upserter.finish()
                stats.total_skipped += skipped_delta
                stats.total_failed += len(to_fetch) - len(results)
            
            # (Note: BatchUpserterBulk handles commits internally or during finish)

        # Logging
        timings["upsert"] = int((time.perf_counter() - phase_start) * 1000)
        timings["total"] = int((time.perf_counter() - total_start) * 1000)
        
        log = log_sync_run(session, started_at, stats, survey_config_id=getattr(settings, "id", "default"), timings=timings)
        session.close()
        
    # Graceful shutdown of persistent API session
    if 'api' in locals():
        await api.close()

    print(f"\n🎉 Cycle selesai!")
    print(f"   {stats}")


async def test_login(settings: Settings):
    print("🧪 Test Mode: Login saja")
    async with async_playwright() as p:
        browser = await launch_stealth_browser(p)
        context = await new_stealth_context(browser, viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        ok, cookies, err_msg = await auto_login(page, settings.sso_username, settings.sso_password)
        if ok:
            print(f"✅ Login berhasil! Didapatkan {len(cookies)} cookies.")
        else:
            print("❌ Login gagal!")

        await context.close()
        await browser.close()


def run_scheduler(settings: Settings):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_sync_cycle,
        trigger=IntervalTrigger(minutes=settings.interval_minutes),
        args=[settings],
        id="fasih_sync",
        name="FASIH-SM Sync Cycle",
        max_instances=1,
        misfire_grace_time=None,
        replace_existing=True,
    )

    print(f"⏰ Scheduler dimulai — interval: {settings.interval_minutes} menit")
    print(f"   Cycle pertama akan berjalan segera + setiap {settings.interval_minutes} menit setelahnya.")
    print(f"   Tekan Ctrl+C untuk berhenti.\n")

    scheduler.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_sync_cycle(settings))
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n🛑 Scheduler dihentikan oleh user.")
        scheduler.shutdown()
    finally:
        loop.close()


def main():
    parser = argparse.ArgumentParser(description="FasihNexus Sync Engine — Sinkronisasi data otomatis")
    parser.add_argument("--once", action="store_true", help="Jalankan 1 cycle saja")
    parser.add_argument("--test-login", action="store_true", help="Test login saja")
    parser.add_argument("--dry-run", action="store_true", help="Enumerate filter tanpa fetch")
    args = parser.parse_args()

    settings = Settings.from_env()
    errors = settings.validate()
    
    if errors and not args.dry_run:
        print("❌ Konfigurasi error:")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    if args.test_login:
        asyncio.run(test_login(settings))
    elif args.once or args.dry_run:
        asyncio.run(run_sync_cycle(settings, dry_run=args.dry_run))
    else:
        run_scheduler(settings)

if __name__ == "__main__":
    main()
