"""
Auth — Automated Login SSO BPS via Keycloak
"""
import os
from datetime import datetime
from typing import Tuple, Dict, Optional
from playwright.async_api import Page


TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

async def launch_stealth_browser(p):
    return await p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]
    )

async def new_stealth_context(browser, **kwargs):
    kwargs.setdefault("ignore_https_errors", True)
    kwargs.setdefault("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    context = await browser.new_context(**kwargs)
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return context


    Returns:
        Tuple[bool, Dict, str]: (Success status, Cookies dictionary, Error message if any)
    """
    FASIH_HOST = TARGET_URL.split("//")[-1]  # fasih-sm.bps.go.id

    try:
        # --- Step 1: Buka halaman login FASIH ---
        print("🔐 Membuka halaman login FASIH...")
        await page.goto(f"{TARGET_URL}/oauth_login.html", wait_until="domcontentloaded", timeout=60000)

        # --- Step 2: Klik tombol "Login SSO BPS" ---
        print("   Mengklik 'Login SSO BPS'...")
        # Coba CSS selector dulu, fallback ke text selector jika FASIH mengubah class
        try:
            await page.wait_for_selector("a.login-button", state="visible", timeout=30000)
            await page.click("a.login-button:has-text('Login SSO BPS')")
        except Exception:
            # Fallback: cari via teks langsung — lebih robust terhadap perubahan HTML
            print("   ⚠️ CSS selector gagal, mencoba text selector...")
            await page.click("text='Login SSO BPS'")

        # --- Step 3: Tunggu redirect ke Keycloak SSO ---
        print("   Menunggu halaman SSO BPS (Keycloak)...")
        await page.wait_for_url("**/sso.bps.go.id/**", timeout=60000)
        await page.wait_for_selector("input#username", state="visible", timeout=30000)

        # --- Step 4: Isi form login ---
        print(f"   Mengisi username: {username[:3]}***")
        await page.fill("input#username", username)
        await page.fill("input#password", password)

        # --- Step 5: Submit ---
        print("   Mengklik 'Log In'...")
        await page.click("input#kc-login")

        # --- Step 6: Tunggu sampai redirect keluar dari Keycloak atau timeout ---
        print("   Menunggu redirect ke dashboard FASIH...")

        # Wait bersyarat: bisa berhasil (ke FASIH), bisa gagal (error Keycloak)
        # Polling setiap 2s, total max 120s
        import asyncio
        deadline = 120
        interval = 2
        for elapsed in range(0, deadline, interval):
            current_url = page.url

            # ✅ Sudah masuk FASIH
            if FASIH_HOST in current_url and "oauth_login" not in current_url:
                print(f"   ✅ Login berhasil setelah {elapsed}s! URL: {current_url[:60]}")
                break

            # ❌ Keycloak menampilkan pesan error (password salah, dll)
            try:
                err_el = await page.query_selector("#input-error, .alert-error, [class*='error-message']")
                if err_el:
                    err_text = await err_el.inner_text()
                    msg = err_text.strip().replace("\n", " ")
                    print(f"   ❌ Keycloak error: {msg}")
                    return False, {}, msg
            except:
                pass

            # ⏳ Masih di Keycloak dan belum ada response — tunggu
            if elapsed > 0 and elapsed % 20 == 0:
                print(f"   ⏳ Masih menunggu... ({elapsed}s)")

            await asyncio.sleep(interval)
        else:
            # Loop selesai tanpa break = timeout
            current_url = page.url
            print(f"   ❌ Login timeout setelah {deadline}s. URL terakhir: {current_url}")
            return False, {}, "Login timeout"

        # Tunggu halaman FASIH sepenuhnya dimuat (non-blocking)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass  # OK jika timeout di sini, kita sudah di URL yang benar

        # Verifikasi final
        current_url = page.url
        if "oauth_login" in current_url or "sso.bps.go.id" in current_url:
            print("   ❌ Login gagal — masih di halaman login. Cek username/password.")
            return False, {}

        print("   ✅ Login berhasil! Fishing for API session maturation...")
        
        # Navigate to a simple API endpoint to force XSRF-TOKEN generation
        try:
            await page.goto(f"{TARGET_URL}/region/api/v1/region/level1?groupId=82af087a-d063-48b9-8633-71c84c4e7422", wait_until="networkidle", timeout=15000)
            print("   🎣 [Auth] API Maturation page loaded.")
        except:
            print("   ⚠️ [Auth] API Maturation page timeout (non-critical).")

        # Ekstrak semua cookies (termasuk F5 security cookies & XSRF)
        cookies = await page.context.cookies()
        cookies_dict = {c['name']: c['value'] for c in cookies}
        return True, cookies_dict, ""
    except Exception as e:
        print(f"   ❌ auto_login exception: {e}")
        return False, {}, str(e)



async def check_session_valid(page: Page) -> bool:
    """
    Cek apakah session masih valid dengan navigasi ringan.
    Jika diredirect ke halaman login, session sudah expired.
    """
    try:
        current_url = page.url
        await page.goto(f"{TARGET_URL}/survey-collection/survey", wait_until="networkidle")
        
        final_url = page.url
        if "oauth_login" in final_url or "sso.bps.go.id" in final_url:
            return False

        # Kembali ke halaman sebelumnya jika session valid
        if current_url and TARGET_URL.split("//")[-1] in current_url:
            await page.goto(current_url, wait_until="networkidle")
        
        return True
    except Exception:
        return False


async def fetch_vpn_cookie(username: str, password: str) -> str | None:
    """
    Otomasi ambil SVPNCOOKIE dari akses.bps.go.id menggunakan Playwright.
    """
    from playwright.async_api import async_playwright
    
    try:
        # Gunakan async_playwright secara lokal untuk isolated browser session
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(browser)
            page = await context.new_page()
            
            start_time = datetime.now()
            print(f"🔐 [{start_time.strftime('%H:%M:%S')}] Membuka portal VPN BPS...")
            # Use 'domcontentloaded' - 'load' will timeout on FortiGate portals with slow tracker scripts
            await page.goto(
                "https://akses.bps.go.id/remote/saml/start",
                wait_until="domcontentloaded",
                timeout=90000
            )
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Menunggu halaman SSO BPS (Keycloak)...")
            await page.wait_for_url("**/sso.bps.go.id/**", timeout=60000)
            await page.wait_for_selector("input#username", state="visible", timeout=60000)
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Mengisi username SSO: {username[:3]}***")
            await page.fill("input#username", username)
            await page.fill("input#password", password)
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Mengklik 'Log In'...")
            await page.click("input#kc-login")
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Menunggu redirect kembali ke portal VPN (bisa memakan waktu 1-3 menit)...")
            # SAML redirect can be slow, increase timeout to 180s for extreme cases
            try:
                await page.wait_for_url("https://akses.bps.go.id/**", timeout=180000)
            except Exception as e:
                # Capture Keycloak error before failing
                err_el = await page.query_selector("#input-error, .alert-error")
                if err_el:
                    txt = await err_el.inner_text()
                    raise Exception(f"Keycloak Error: {txt.strip()}")
                raise e

            await page.wait_for_load_state("load")
            
            # Ekstrak cookies dari context VPN
            cookies = await context.cookies()
            vpn_cookie = None
            for c in cookies:
                if c["name"] == "SVPNCOOKIE":
                    vpn_cookie = f"SVPNCOOKIE={c['value']}"
                    break
            
            if vpn_cookie:
                duration = (datetime.now() - start_time).total_seconds()
                print(f"   ✅ [{datetime.now().strftime('%H:%M:%S')}] Berhasil mendapatkan SVPNCOOKIE dalam {duration:.1f}s")
            else:
                print(f"   ❌ [{datetime.now().strftime('%H:%M:%S')}] Gagal mendapatkan SVPNCOOKIE setelah login")
                
            await browser.close()
            return vpn_cookie

    except Exception as e:
        print(f"   ❌ Error VPN auto-fetch: {e}")
        return None
