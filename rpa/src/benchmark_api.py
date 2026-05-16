"""
benchmark_api.py — Benchmark kecepatan tarik data FASIH-SM

Mengikuti flow IDENTIK dengan main.py (RPA engine produksi):
  Fase 0: Decrypt SSO credentials dari DB
  Fase 1: Login SSO via Playwright → dapatkan fresh cookies
  Fase 2: Benchmark endpoint resolusi metadata survey
  Fase 3: Benchmark endpoint resolusi region & period
  Fase 4: Benchmark assignment datatable (throughput riil)
  Fase 5: Benchmark detail assignment (sample 5 records)

Jalankan: docker exec -w /app/src cdc-rpa python benchmark_api.py
"""

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def hr(char="─", width=70):
    print(char * width)

def section(title: str):
    print()
    hr("═")
    print(f"  {title}")
    hr("═")

def step(label: str):
    print(f"\n▶  {label}")
    hr("─")

def result(key: str, val, unit=""):
    print(f"   {'·'} {key:<38} {val} {unit}")

def warn(msg: str):
    print(f"   ⚠  {msg}")

def fail(msg: str):
    print(f"   ✗  {msg}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Decrypt password: format iv_hex:cipher_hex (AES-256-CBC) dari dashboard
# ─────────────────────────────────────────────────────────────────────────────

def decrypt_aes_cbc(encrypted_str: str) -> str:
    """Decrypt AES-256-CBC format: 'iv_hex:ciphertext_hex' (digunakan oleh Dashboard TS).
    
    Key derivation: SHA-256(key_string) — identik dengan Node.js:
      createHash('sha256').update(ENCRYPTION_KEY).digest()
    """
    import hashlib
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    key_str = os.environ.get("ENCRYPTION_KEY", "")
    if not key_str:
        raise ValueError("ENCRYPTION_KEY tidak di-set di environment")

    parts = encrypted_str.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Format encrypted tidak dikenali: {encrypted_str[:30]}")

    iv = bytes.fromhex(parts[0])
    ct = bytes.fromhex(parts[1])
    # Derive key: SHA-256 dari KEY STRING (bukan hex-decode) — sama dengan Node.js dashboard
    key = hashlib.sha256(key_str.encode()).digest()  # 32 bytes

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    # PKCS7 unpad
    pad_len = padded[-1]
    return padded[:-pad_len].decode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Fase 0: Baca config dari DB
# ─────────────────────────────────────────────────────────────────────────────

def load_survey_config():
    """Pilih survey dengan jumlah records di DB antara 50–1000 (cukup besar untuk
    throughput yang bermakna, cukup kecil agar benchmark selesai cepat).
    Fallback ke survey aktif pertama jika tidak ada yang masuk range."""
    from db.connection import get_session
    from db.models import SurveyConfig, Assignment
    from sqlalchemy import func

    session = get_session()
    # Hitung jumlah assignment per survey_config_id
    counts = (
        session.query(Assignment.survey_config_id, func.count(Assignment.id).label("cnt"))
        .group_by(Assignment.survey_config_id)
        .all()
    )
    count_map = {str(cid): cnt for cid, cnt in counts}

    # Pilih survey aktif yang masuk range 50–1000 records, urutkan terbanyak dulu
    active_surveys = session.query(SurveyConfig).filter_by(is_active=True).all()
    candidates = [
        (sc, count_map.get(str(sc.id), 0))
        for sc in active_surveys
        if 50 <= count_map.get(str(sc.id), 0) <= 1000
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)  # terbanyak dulu dalam range

    if candidates:
        chosen, cnt = candidates[0]
        print(f"  Auto-selected: '{chosen.survey_name}' ({cnt} records di DB)")
        session.close()
        return chosen

    # Fallback: survey aktif pertama
    warn("Tidak ada survey dengan 50–1000 records, menggunakan survey aktif pertama.")
    sc = active_surveys[0] if active_surveys else None
    session.close()
    if not sc:
        fail("Tidak ada SurveyConfig aktif di database.")
    return sc


# ─────────────────────────────────────────────────────────────────────────────
# Cookie probe: cek apakah cookies di DB masih valid tanpa login ulang
# ─────────────────────────────────────────────────────────────────────────────

async def probe_cookies(cookies: dict) -> bool:
    """Kirim satu request ringan ke API survey list.
    Return True jika server memberi JSON (session valid), False jika redirect HTML."""
    import aiohttp, ssl
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    xsrf = cookies.get("XSRF-TOKEN", "")
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{TARGET_URL}/",
        "X-XSRF-TOKEN": xsrf,
        "Cookie": cookie_str,
    }
    try:
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_ctx)
        ) as s:
            # Endpoint ringan: survey list page 0 size 1
            payload = {"pageNumber": 0, "pageSize": 1, "sortBy": "CREATED_AT",
                       "sortDirection": "DESC", "keywordSearch": ""}
            async with s.post(
                f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                ct = r.headers.get("content-type", "")
                return "application/json" in ct
    except Exception:
        return False


async def get_valid_cookies(sc, password: str) -> tuple:
    """Ambil cookies valid: reuse dari DB jika masih aktif, login ulang jika tidak.
    Returns (cookies_dict, login_ms, reused: bool)"""
    from db.connection import get_session as _gs
    from db.models import SystemSettings

    # Coba cookies dari DB dulu
    try:
        dbs = _gs()
        rec = dbs.query(SystemSettings).filter_by(key="sso_cookies").first()
        dbs.close()
        if rec and rec.value:
            cached = json.loads(rec.value)
            print("  Memeriksa cookies DB yang tersimpan...")
            t0 = time.perf_counter()
            valid = await probe_cookies(cached)
            probe_ms = (time.perf_counter() - t0) * 1000
            if valid:
                print(f"  ✓ Cookies DB masih valid (probe {probe_ms:.0f} ms) — skip Playwright login.")
                return cached, probe_ms, True
            else:
                print(f"  ✗ Cookies DB sudah expired (probe {probe_ms:.0f} ms) — login ulang via Playwright.")
    except Exception as e:
        warn(f"Probe cookies DB gagal: {e}")

    # Fallback: login via Playwright
    from playwright.async_api import async_playwright
    from auth import auto_login
    t0 = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        login_ok, cookies_dict, err_msg = await auto_login(page, sc.sso_username, password)
        await browser.close()
    login_ms = (time.perf_counter() - t0) * 1000
    if not login_ok or not cookies_dict:
        fail("Login SSO gagal — pastikan VPN connected dan credentials valid.")
    # Simpan cookies segar ke DB
    try:
        dbs = _gs()
        setting = dbs.query(SystemSettings).filter_by(key="sso_cookies").first()
        if setting:
            setting.value = json.dumps(cookies_dict)
        else:
            from db.models import SystemSettings as _SS
            setting = _SS(key="sso_cookies", value=json.dumps(cookies_dict))
            dbs.add(setting)
        dbs.commit()
        dbs.close()
        print("   💾 Cookies baru disimpan ke DB.")
    except Exception as e:
        warn(f"Gagal simpan cookies ke DB: {e}")
    return cookies_dict, login_ms, False


# ─────────────────────────────────────────────────────────────────────────────
# Main benchmark
# ─────────────────────────────────────────────────────────────────────────────

async def run_benchmark():
    section("🚀 BENCHMARK KECEPATAN TARIK DATA FASIH-SM")
    print(f"  Target  : {TARGET_URL}")
    print(f"  Waktu   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode    : Identik dengan flow RPA Produksi (main.py)\n")

    timings = {}   # dict label → ms
    results_summary = []

    # ── Fase 0: Load config ──────────────────────────────────────────────────
    step("Fase 0 · Load Survey Config dari DB")
    sc = load_survey_config()
    result("Survey", sc.survey_name)
    result("Username", sc.sso_username)
    result("Filter Provinsi", sc.filter_provinsi)
    result("Filter Kabupaten", sc.filter_kabupaten)
    result("Filter Rotation", sc.filter_rotation)

    # Decrypt password dengan AES-CBC (format dashboard)
    try:
        password = decrypt_aes_cbc(sc.sso_password_encrypted)
        result("Password decrypted", f"{'*' * len(password)} ({len(password)} chars)")
    except Exception as e:
        fail(f"Gagal decrypt password: {e}")

    # ── Fase 1: Autentikasi (reuse cookies DB atau login Playwright) ──────────
    step("Fase 1 · Autentikasi SSO")
    cookies, login_ms, reused = await get_valid_cookies(sc, password)
    timings["login_sso"] = login_ms
    login_label = "Reuse cookies DB (probe)" if reused else "Login via Playwright"
    result(login_label, f"{login_ms:.0f}", "ms")
    result("Cookies diperoleh", len(cookies), "keys")
    results_summary.append((f"Auth — {login_label}", f"{login_ms:.0f} ms"))

    # ── Fase 2-5: Benchmark API ───────────────────────────────────────────────
    from api_client import FasihApiClient

    async with FasihApiClient(cookies) as api:

        # Fase 2: Resolve Survey ID
        step("Fase 2 · Resolusi Survey ID (Endpoint: /survey/api/v1/surveys/datatable)")
        t0 = time.perf_counter()
        survey_id = await api.get_survey_id(sc.survey_name)
        ms = (time.perf_counter() - t0) * 1000
        timings["survey_lookup"] = ms

        if not survey_id:
            fail(f"Survey '{sc.survey_name}' tidak ditemukan di FASIH-SM.")

        result("Survey ID resolved", survey_id[:12] + "...")
        result("Latency resolusi survey", f"{ms:.1f}", "ms")
        results_summary.append(("Survey ID lookup", f"{ms:.0f} ms"))

        # Fase 3a: Period & Roles
        step("Fase 3a · Resolusi Periode & Role (Endpoints: /survey-periods, /survey-roles)")
        t0 = time.perf_counter()
        period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)
        ms = (time.perf_counter() - t0) * 1000
        timings["period_roles"] = ms

        if not period_id:
            fail("Periode survey tidak ditemukan.")

        result("Period ID", period_id[:12] + "...")
        result("Role count", len(role_ids))
        result("Role Group ID", (role_group_id or "N/A")[:12] + "..." if role_group_id else "N/A")
        result("Latency periode+role", f"{ms:.1f}", "ms")
        results_summary.append(("Period & Roles lookup", f"{ms:.0f} ms"))

        # Fase 3b: Region Metadata
        step("Fase 3b · Resolusi Region (Endpoints: /region/api/v1/region/level1+2)")
        t0 = time.perf_counter()
        prov_uuid, region_uuid, region_full_code, region_group_id2 = await api.get_region_metadata(
            sc.filter_provinsi, sc.filter_kabupaten, survey_id
        )
        ms = (time.perf_counter() - t0) * 1000
        timings["region_metadata"] = ms

        result("Provinsi UUID", (prov_uuid or "N/A")[:12] + "..." if prov_uuid else "N/A")
        result("Kabupaten UUID", (region_uuid or "N/A")[:12] + "..." if region_uuid else "N/A")
        result("Region Full Code", region_full_code or "N/A")
        result("Latency resolusi region", f"{ms:.1f}", "ms")
        results_summary.append(("Region metadata lookup", f"{ms:.0f} ms"))

        # Fase 3c: Users by Region (pengawas/pencacah list)
        step("Fase 3c · List Pengawas/Pencacah (Endpoints: /survey-period-role-users/region + datatable)")
        t0 = time.perf_counter()
        pengawas_list, pencacah_list = await api.get_users_by_region(
            period_id, role_ids, region_uuid or region_full_code or "", role_group_id
        )
        ms = (time.perf_counter() - t0) * 1000
        timings["users_by_region"] = ms

        result("Pengawas/Admin ditemukan", len(pengawas_list), "orang")
        result("Pencacah ditemukan", len(pencacah_list), "orang")
        result("Latency list user", f"{ms:.1f}", "ms")
        results_summary.append(("Users by region", f"{ms:.0f} ms  ({len(pengawas_list)} pengawas, {len(pencacah_list)} pencacah)"))

        # Fase 4: Assignment Datatable — THROUGHPUT TEST
        step("Fase 4 · Throughput Assignment Datatable (Endpoint: /analytic/api/v2/assignment/datatable-all-user-survey-periode)")
        print(f"  Filter: periode={period_id[:8]}... | prov={prov_uuid and prov_uuid[:8]}... | kab={region_uuid and region_uuid[:8]}...")
        print(f"  (Menarik semua halaman dengan page_size=1000 — identik dengan sync riil)")

        t0 = time.perf_counter()
        assignments = await api.get_assignments_metadata(
            period_id=period_id,
            prov_uuid=prov_uuid,
            kab_uuid=region_uuid if region_uuid != prov_uuid else None,
            region_group_id=region_group_id2 or role_group_id,
        )
        ms = (time.perf_counter() - t0) * 1000
        timings["assignments_datatable"] = ms

        n = len(assignments)
        rps = n / (ms / 1000) if ms > 0 and n > 0 else 0
        result("Total records dari API", n, "records")
        result("Waktu total fetch datatable", f"{ms:.0f}", "ms")
        if n > 0:
            result("Throughput datatable", f"{rps:.1f}", "records/detik")
            results_summary.append((
                "Assignment datatable throughput",
                f"{n} records dalam {ms:.0f} ms → {rps:.1f} rec/s"
            ))
        else:
            # API return 0 — akun ini mungkin tidak punya akses datatable.
            # Cek jumlah records yang sudah tersimpan di DB lokal sebagai konteks.
            from db.connection import get_session as _gs2
            from db.models import Assignment
            from sqlalchemy import func
            _dbs = _gs2()
            db_count = _dbs.query(func.count(Assignment.id)).filter_by(survey_config_id=sc.id).scalar()
            _dbs.close()
            warn(f"Datatable API return 0 — akun mungkin tidak memiliki akses view-all.")
            warn(f"Records tersimpan di DB lokal untuk survey ini: {db_count} records")
            results_summary.append((
                "Assignment datatable throughput",
                f"0 from API (DB lokal: {db_count} records)"
            ))

        # Fase 5: Assignment Detail — SAMPLE latency
        step("Fase 5 · Latency Detail Assignment (Endpoint: /assignment-general/api/assignment/get-by-id-with-data-for-scm)")
        sample_ids = [m["id"] for m in assignments[:5]] if assignments else []

        # Fallback: ambil sample ID dari DB lokal jika datatable API return 0
        if not sample_ids:
            warn("Datatable return 0 — menggunakan sample IDs dari DB lokal untuk uji latency detail.")
            from db.connection import get_session as _gs3
            from db.models import Assignment
            _dbs3 = _gs3()
            db_samples = _dbs3.query(Assignment).filter_by(survey_config_id=sc.id).limit(5).all()
            _dbs3.close()
            sample_ids = [str(a.id) for a in db_samples]
            if sample_ids:
                print(f"   Menggunakan {len(sample_ids)} IDs dari DB lokal.")

        if not sample_ids:
            warn("Tidak ada assignment ID yang bisa digunakan untuk uji detail.")
        else:
            detail_times = []
            for aid in sample_ids:
                t0 = time.perf_counter()
                detail = await api.get_assignment_detail(aid)
                ms_d = (time.perf_counter() - t0) * 1000
                detail_times.append(ms_d)
                status = "✓ OK" if detail else "✗ None"
                print(f"   {status}  ID={aid[:8]}...  latency={ms_d:.1f} ms")

            avg_detail = sum(detail_times) / len(detail_times)
            min_detail = min(detail_times)
            max_detail = max(detail_times)
            timings["detail_avg_ms"] = avg_detail

            result("Latency detail — rata-rata", f"{avg_detail:.1f}", "ms")
            result("Latency detail — min", f"{min_detail:.1f}", "ms")
            result("Latency detail — maks", f"{max_detail:.1f}", "ms")
            results_summary.append((
                "Assignment detail latency (avg)",
                f"{avg_detail:.1f} ms (sample {len(sample_ids)})"
            ))

        # Fase 6: Deep Dive Verification (Smart Slicing)
        step("Fase 6 · Verifikasi Deep Dive (Endpoint: /region/api/v1/region/level3)")
        if region_full_code and region_group_id2:
            t0 = time.perf_counter()
            sub_regions = await api.get_sub_regions(3, region_group_id2, region_full_code)
            ms = (time.perf_counter() - t0) * 1000
            
            result("Parent Region Code", region_full_code)
            result("Sub-regions found (Level 3)", len(sub_regions))
            result("Latency Level 3 lookup", f"{ms:.1f}", "ms")
            
            if sub_regions:
                sample_sub = sub_regions[0]
                result("Sample Sub-region", f"{sample_sub.get('name')} ({sample_sub.get('fullCode')})")
                results_summary.append(("Deep Dive Capability", f"✅ Found {len(sub_regions)} sub-regions for {region_full_code}"))
            else:
                warn(f"Tidak ada sub-wilayah (Kecamatan) ditemukan untuk {region_full_code}. Verifikasi logic slicing manual diperlukan.")
                results_summary.append(("Deep Dive Capability", "⚠ No sub-regions (L3) returned"))
        else:
            warn("Data region tidak lengkap (Missing Full Code/Group ID). Skip verifikasi Deep Dive.")
            results_summary.append(("Deep Dive Capability", "✗ Skipped (Missing metadata)"))

    # ─────────────────────────────────────────────────────────────────────────
    # Ringkasan akhir
    # ─────────────────────────────────────────────────────────────────────────
    section("📊 RINGKASAN BENCHMARK")
    print(f"  {'Endpoint / Fase':<42} {'Hasil':>28}")
    hr()
    for label, val in results_summary:
        print(f"  {label:<42} {val:>28}")
    hr()

    total_api_ms = sum(v for k, v in timings.items() if k != "login_sso")
    print(f"\n  Total waktu API (tanpa login) : {total_api_ms:.0f} ms")
    print(f"  Total waktu termasuk login    : {total_api_ms + timings.get('login_sso', 0):.0f} ms")
    print()
    print("  ✓ Gunakan angka throughput Fase 4 sebagai baseline perbandingan antar-env.")
    print("  ✓ Simpan output ini untuk audit performa sinkronisasi ke depannya.")
    hr("═")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
