"""
FASIH-SM RPA Sync — Main Orchestrator

Fully automated robot yang:
1. Login SSO BPS otomatis
2. Navigasi ke survey target
3. Rotate filter per pengawas/pencacah (bypass limit 1000 baris)
4. Fetch data assignment via API langsung
5. Upsert ke SQLite
6. Berjalan otomatis setiap N menit

Usage:
    python src/main.py                  # Start scheduler (loop setiap 30 menit)
    python src/main.py --once           # Jalankan 1 cycle saja
    python src/main.py --test-login     # Test login saja
    python src/main.py --dry-run        # Enumerate filter, print stats (tanpa fetch)
"""
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

# Tambahkan parent dir ke path agar bisa import config/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import Settings
from auth import auto_login
from pages.survey_navigator import find_survey_id, navigate_to_data_tab
from pages.filter_rotator import (
    iterate_filters,
    get_total_entries,
    click_reset,
    open_filter_sidebar,
)
from pages.assignment_page import inject_page_size_1000, get_all_assignment_links
from pages.detail_page import fetch_assignment_data
from db.connection import init_db, get_session
from db.repository import upsert_assignment, log_sync_run, SyncStats


async def run_sync_cycle(settings: Settings, dry_run: bool = False):
    """
    Satu siklus lengkap sinkronisasi:
    Login → Navigate → Rotate Filter → Fetch → Upsert → Log
    """
    started_at = datetime.now(timezone.utc)
    stats = SyncStats()
    
    print("\n" + "=" * 60)
    print(f"🤖 FASIH-SM RPA Sync — Cycle dimulai")
    print(f"   Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Survey: {settings.survey_name}")
    print(f"   Rotasi: {settings.filter_rotation}")
    print(f"   Dry run: {dry_run}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        
        try:
            page = await context.new_page()

            # --- FASE 1: LOGIN ---
            print("\n--- FASE 1: Login SSO BPS ---")
            login_ok = await auto_login(page, settings.sso_username, settings.sso_password)
            if not login_ok:
                print("❌ Login gagal! Cycle dibatalkan.")
                return

            # --- FASE 2: NAVIGASI KE SURVEY ---
            print("\n--- FASE 2: Navigasi ke Survey ---")
            survey_id = await find_survey_id(page, settings.survey_name)
            if not survey_id:
                print("❌ Survey tidak ditemukan! Cycle dibatalkan.")
                return
            
            nav_ok = await navigate_to_data_tab(page, survey_id)
            if not nav_ok:
                print("❌ Gagal membuka tab Data! Cycle dibatalkan.")
                return

            # --- FASE 3: ROTATE FILTER & FETCH ---
            print("\n--- FASE 3: Rotate Filter & Fetch Data ---")
            
            # DB path per survey: data/{survey_slug}/sync.db
            survey_slug = re.sub(r'[^a-z0-9]+', '_', settings.survey_name.lower()).strip('_')
            survey_data_dir = os.path.join(os.path.dirname(settings.db_path), survey_slug)
            survey_db_path = os.path.join(survey_data_dir, "sync.db")
            
            if not dry_run:
                init_db(survey_db_path)
                session = get_session(survey_db_path)
                print(f"   📂 Data dir: {survey_data_dir}/")

            async for pengawas, pencacah in iterate_filters(
                page,
                provinsi=settings.filter_provinsi,
                kabupaten=settings.filter_kabupaten,
                rotation=settings.filter_rotation,
            ):
                filter_label = f"Pengawas={pengawas or 'ALL'}"
                if pencacah:
                    filter_label += f", Pencacah={pencacah}"
                
                # Apply sudah dilakukan di iterate_filters,
                # filter_rotator memanggil apply_full_filter sendiri.
                # Kita hanya perlu inject page size 1000.
                
                # Inject page size 1000
                await inject_page_size_1000(page)
                
                total = await get_total_entries(page)
                print(f"   📊 {filter_label} → {total} entries")

                if dry_run:
                    stats.total_fetched += total
                    continue

                # Scrape links
                links = await get_all_assignment_links(page)
                print(f"   🔗 {len(links)} link ditemukan")

                # Fetch setiap assignment via API
                for i, url in enumerate(links):
                    data = await fetch_assignment_data(page, url)
                    stats.total_fetched += 1

                    if data:
                        result = upsert_assignment(session, data, stats)
                        identity = data.get("code_identity", "?")
                        symbol = {"new": "🆕", "updated": "🔄", "skipped": "⏭️"}.get(result, "❓")
                        
                        # Print progress setiap 10 records atau di awal
                        if i < 3 or (i + 1) % 10 == 0 or i == len(links) - 1:
                            print(f"     [{i+1}/{len(links)}] {symbol} {identity} ({result})")
                    else:
                        stats.total_failed += 1

                    # Jeda agar tidak di-rate-limit
                    await asyncio.sleep(0.3)

                # Commit per-batch (per pengawas/pencacah)
                if not dry_run:
                    session.commit()

            # --- FASE 4: LOG ---
            print("\n--- FASE 4: Logging ---")
            if not dry_run:
                log = log_sync_run(session, started_at, stats)
                session.close()
            
            print(f"\n🎉 Cycle selesai!")
            print(f"   {stats}")

        except Exception as e:
            print(f"\n❌ Error dalam cycle: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await context.close()
            await browser.close()


async def test_login(settings: Settings):
    """Test login saja, tanpa fetch data."""
    print("🧪 Test Mode: Login saja")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        ok = await auto_login(page, settings.sso_username, settings.sso_password)
        if ok:
            print("✅ Login berhasil! Browser akan ditutup dalam 5 detik...")
            await asyncio.sleep(5)
        else:
            print("❌ Login gagal!")

        await context.close()
        await browser.close()


def run_scheduler(settings: Settings):
    """Jalankan scheduler yang menjalankan cycle setiap N menit."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        run_sync_cycle,
        trigger=IntervalTrigger(minutes=settings.interval_minutes),
        args=[settings],
        id="fasih_sync",
        name="FASIH-SM Sync Cycle",
        max_instances=1,  # Tidak overlap jika cycle > interval
        misfire_grace_time=None,  # Jalankan jika terlewat
        replace_existing=True,
    )

    print(f"⏰ Scheduler dimulai — interval: {settings.interval_minutes} menit")
    print(f"   Cycle pertama akan berjalan segera + setiap {settings.interval_minutes} menit setelahnya.")
    print(f"   Tekan Ctrl+C untuk berhenti.\n")

    scheduler.start()

    # Jalankan cycle pertama langsung
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(run_sync_cycle(settings))
        # Setelah cycle pertama selesai, biarkan scheduler berjalan
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n🛑 Scheduler dihentikan oleh user.")
        scheduler.shutdown()
    finally:
        loop.close()


def main():
    parser = argparse.ArgumentParser(
        description="FASIH-SM RPA Sync — Sinkronisasi data otomatis"
    )
    parser.add_argument("--once", action="store_true", help="Jalankan 1 cycle saja")
    parser.add_argument("--test-login", action="store_true", help="Test login saja")
    parser.add_argument("--dry-run", action="store_true", help="Enumerate filter tanpa fetch")
    args = parser.parse_args()

    # Load settings
    settings = Settings.from_env()
    errors = settings.validate()
    
    if errors and not args.dry_run:
        print("❌ Konfigurasi error:")
        for err in errors:
            print(f"   - {err}")
        print("\nSalin config/.env.example → config/.env dan isi nilainya.")
        sys.exit(1)

    if args.test_login:
        asyncio.run(test_login(settings))
    elif args.once or args.dry_run:
        asyncio.run(run_sync_cycle(settings, dry_run=args.dry_run))
    else:
        run_scheduler(settings)


if __name__ == "__main__":
    main()
