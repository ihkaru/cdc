"""
Auth — Automated Login SSO BPS via Keycloak
"""
import os
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
        True jika berhasil login, False jika gagal
    """
    try:
        # --- Step 1: Buka halaman login FASIH ---
        print("🔐 Membuka halaman login FASIH...")
        await page.goto(f"{TARGET_URL}/oauth_login.html", wait_until="networkidle")

        # --- Step 2: Klik tombol "Login SSO BPS" ---
        print("   Mengklik 'Login SSO BPS'...")
        await page.click("a.login-button:has-text('Login SSO BPS')")

        # --- Step 3: Tunggu redirect ke Keycloak SSO ---
        print("   Menunggu halaman SSO BPS (Keycloak)...")
        await page.wait_for_url("**/sso.bps.go.id/**", timeout=15000)
        await page.wait_for_selector("input#username", state="visible", timeout=10000)

        # --- Step 4: Isi form login ---
        print(f"   Mengisi username: {username[:3]}***")
        await page.fill("input#username", username)
        await page.fill("input#password", password)

        # --- Step 5: Submit ---
        print("   Mengklik 'Log In'...")
        await page.click("input#kc-login")

        # --- Step 6: Tunggu redirect kembali ke FASIH ---
        print("   Menunggu redirect ke dashboard FASIH...")
        await page.wait_for_url(f"**/{TARGET_URL.split('//')[-1]}/**", timeout=30000)
        
        # Tunggu navigasi selesai
        await page.wait_for_load_state("networkidle")

        # Verifikasi — cek apakah kita sudah di halaman yang benar (bukan login lagi)
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
