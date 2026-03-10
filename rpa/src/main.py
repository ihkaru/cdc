"""
FASIH-SM RPA Sync — Main Orchestrator (API First)

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
from datetime import datetime, timezone

from playwright.async_api import async_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import Settings
from auth import auto_login
from api_client import FasihApiClient
from pages.detail_page import fetch_assignments_concurrent
from db.connection import init_db, get_session
from db.repository import upsert_assignment, log_sync_run, SyncStats


async def run_sync_cycle(settings: Settings, dry_run: bool = False):
    """
    Satu siklus lengkap sinkronisasi Hybrid-Headless.
    """
    started_at = datetime.now(timezone.utc)
    stats = SyncStats()
    
    print("\n" + "=" * 60)
    print(f"🤖 FASIH-SM API Sync — Cycle dimulai")
    print(f"   Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Survey: {settings.survey_name}")
    print(f"   Rotasi: {settings.filter_rotation}")
    print(f"   Dry run: {dry_run}")
    print("=" * 60)

    # --- FASE 1: LOGIN SSO via PLAYWRIGHT ---
    print("\n--- FASE 1: Login SSO BPS ---")
    cookies = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        login_ok, cookies_dict = await auto_login(page, settings.sso_username, settings.sso_password)
        if not login_ok or not cookies_dict:
            print("❌ Login gagal! Cycle dibatalkan.")
            await browser.close()
            return
            
        cookies = cookies_dict
        await browser.close()
        
    print(f"   🔑 Didapatkan {len(cookies)} cookies. Melanjutkan ke mode API murni.")

    # Inisialisasi API Client
    api = FasihApiClient(cookies)

    # --- FASE 2: RESOLVE METADATA SURVEY & REGION ---
    print("\n--- FASE 2: Resolving API Metadata ---")
    survey_id = await api.get_survey_id(settings.survey_name)
    if not survey_id:
        return

    period_id, role_ids = await api.get_survey_period_and_roles(survey_id)
    if not period_id or not role_ids:
        return

    prov_code, region_filter, region_full_code, region_group_id = await api.get_region_metadata(settings.filter_provinsi, settings.filter_kabupaten, survey_id)
    
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
    
    pengawas_list, pencacah_list = await api.get_users_by_region(period_id, role_ids, region_filter)
    
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
    
    for f in filters_to_run:
        print(f"\n🔄 {f['label']}")
        metadata = await api.get_assignments_metadata(
            period_id, 
            prov_uuid=prov_code,
            kab_uuid=region_filter if region_filter != prov_code else None,
            pengawas_id=f['pengawas_id'], 
            pencacah_id=f['pencacah_id'],
            region_group_id=region_group_id
        )
        print(f"   📊 Ditemukan {len(metadata)} entries.")
        
        for m in metadata:
            all_metadata_map[m['id']] = m

    unique_assignments = list(all_metadata_map.values())
    print(f"\n--- FASE 4: Fetch Detailed Assignment Data ---")
    print(f"   🔗 Total Assignment Unik: {len(unique_assignments)}")
    
    if dry_run:
        stats.total_fetched = len(unique_assignments)
    else:
        if unique_assignments:
            urls_to_fetch = [
                f"{os.getenv('TARGET_URL', 'https://fasih-sm.bps.go.id')}/survey-collection/assignment-detail/{m['id']}/{survey_id}" 
                for m in unique_assignments
            ]
            
            # Fetch secara concurrent
            results = await fetch_assignments_concurrent(cookies, urls_to_fetch, concurrency=20)
            
            # Upsert
            print("\n   💾 Menyimpan ke database...")
            for i, data in enumerate(results):
                stats.total_fetched += 1
                result_status = upsert_assignment(session, data, stats)
                identity = data.get("code_identity", "?")
                symbol = {"new": "🆕", "updated": "🔄", "skipped": "⏭️"}.get(result_status, "❓")
                
                # Print sample progress
                if i < 3 or (i + 1) % 50 == 0 or i == len(results) - 1:
                    print(f"     [{i+1}/{len(results)}] {symbol} {identity} ({result_status})")
                    
            stats.total_failed = len(unique_assignments) - len(results)
            session.commit()

        # Logging
        log = log_sync_run(session, started_at, stats)
        session.close()

    print(f"\n🎉 Cycle selesai!")
    print(f"   {stats}")


async def test_login(settings: Settings):
    print("🧪 Test Mode: Login saja")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=100)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        ok, cookies = await auto_login(page, settings.sso_username, settings.sso_password)
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
    parser = argparse.ArgumentParser(description="FASIH-SM RPA Sync — Sinkronisasi data otomatis")
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
