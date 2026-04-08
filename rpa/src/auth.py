"""
Auth — Automated Login SSO BPS via Keycloak
"""
import os
from datetime import datetime
from playwright.async_api import Page

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")


async def auto_login(page: Page, username: str, password: str) -> bool:
    """
    Otomasi login SSO BPS:
    1. Buka halaman login FASIH
    2. Klik "Login SSO BPS"
    3. Isi username + password di form Keycloak
    4. Submit dan tunggu redirect ke dashboard

    Returns:
        bool: True jika login berhasil
    """
    FASIH_HOST = TARGET_URL.split("//")[-1]  # fasih-sm.bps.go.id

    try:
        # --- Step 1: Buka halaman login FASIH ---
        print("🔐 Membuka halaman login FASIH...")
        await page.goto(f"{TARGET_URL}/oauth_login.html", wait_until="domcontentloaded", timeout=60000)

        # --- Step 2: Klik tombol "Login SSO BPS" ---
        print("   Mengklik 'Login SSO BPS'...")
        await page.wait_for_selector("a.login-button", state="visible", timeout=15000)
        await page.click("a.login-button:has-text('Login SSO BPS')")

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
                    print(f"   ❌ Keycloak error: {err_text.strip()}")
                    return False
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
            return False

        # Tunggu halaman FASIH sepenuhnya dimuat (non-blocking)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass  # OK jika timeout di sini, kita sudah di URL yang benar

        # Verifikasi final
        current_url = page.url
        if "oauth_login" in current_url or "sso.bps.go.id" in current_url:
            print("   ❌ Login gagal — masih di halaman login. Cek username/password.")
            return False

        print("   ✅ Login berhasil!")
        return True

    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False



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
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            
            start_time = datetime.now()
            print(f"🔐 [{start_time.strftime('%H:%M:%S')}] Membuka portal VPN BPS...")
            # Use 'load' instead of 'networkidle' as the portal might have slow background trackers
            await page.goto("https://akses.bps.go.id/remote/saml/start", wait_until="load", timeout=60000)
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Menunggu halaman SSO BPS (Keycloak)...")
            await page.wait_for_url("**/sso.bps.go.id/**", timeout=60000)
            await page.wait_for_selector("input#username", state="visible", timeout=60000)
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Mengisi username SSO: {username[:3]}***")
            await page.fill("input#username", username)
            await page.fill("input#password", password)
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Mengklik 'Log In'...")
            await page.click("input#kc-login")
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Menunggu redirect kembali ke portal VPN (bisa memakan waktu 1-2 menit)...")
            # SAML redirect can be slow, increase timeout to 120s
            await page.wait_for_url("https://akses.bps.go.id/**", timeout=120000)
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
