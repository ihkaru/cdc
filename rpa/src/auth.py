import os
import asyncio
import psycopg2
import json
from playwright.async_api import async_playwright

# Global lock to prevent multiple simultaneous Playwright sessions for cookie fetching
FETCH_LOCK = asyncio.Lock()

async def get_current_cookie():
    """Retrieve the current vpn_cookie from the database."""
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_settings WHERE key = 'vpn_cookie'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

async def launch_stealth_browser(p):
    """Launch a browser optimized for BPS portal compatibility."""
    return await p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-http2', # Critical: BPS Portal handles HTTP/1.1 better
        ]
    )

async def perform_sso_login(page, username, password, target_url="https://fasih-sm.bps.go.id"):
    """
    Core logic to perform SAML login on a given page.
    Returns (success, error_message)
    """
    try:
        # 1. Early check: Are we already on Keycloak/SSO?
        if "sso.bps.go.id" in page.url:
            print("   🔒 [Auth] Already on Keycloak SSO. Filling credentials...")
        else:
            # 2. Navigate to Target App directly
            target_domain = target_url.split("://")[1].split("/")[0]
            if target_domain not in page.url and "sso.bps.go.id" not in page.url:
                print(f"🚀 [Auth] Navigating to target {target_domain}...")
                await page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
                
                # Apply 5-Second Stabilization Rule specifically for VPN Portal (akses.bps.go.id)
                if "akses.bps.go.id" in target_url:
                    print("   ⏳ [Auth] Waiting 5s for VPN Portal background scripts to stabilize...")
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
            
            # 3. Wait for SAML Button or FASIH-SM SSO Selection
            print(f"🚀 [Auth] Detecting SSO/SAML login button...")
            saml_selectors = [
                "#saml-login-bn", 
                ".btn-saml", 
                "button:has-text('Login SSO')", 
                "button:has-text('SAML')",
                "a[href*='/oauth2/authorization/ics']",
                "a:has-text('Login SSO BPS')"
            ]
            combined_selector = ", ".join(saml_selectors)
            
            try:
                await page.wait_for_selector(combined_selector, timeout=60000)
                # We wait 1s for event listeners to attach
                await asyncio.sleep(1) 
                print("   🖱️ [Auth] Clicking SSO/SAML button...")
                await page.click(combined_selector, force=True)
            except Exception:
                print("   ⚠️ [Auth] SSO button not found or not needed. Checking for SSO redirect...")
                # We don't return False here, we let the next block handle Keycloak

        # 4. Transition to Keycloak (SSO)
        print(f"🚀 [Auth] Handling Keycloak SSO... Current URL: {page.url}")
        try:
            # Wait for the SSO page input to be ready
            await page.wait_for_selector("#username", timeout=60000)
            print(f"   ✅ [Auth] SSO Page reached: {page.url}")
        except Exception as e:
            print(f"   ❌ [Auth] Timeout waiting for #username. Stuck at URL: {page.url}")
            if "sso.bps.go.id" not in page.url:
                return False, f"Gagal dialihkan ke SSO: {str(e)}"
            else:
                return False, f"Berada di SSO tapi #username tidak ditemukan. URL: {page.url}"
        
        # 5. Fill Credentials
        print(f"🚀 [Auth] Filling credentials...")
        await page.fill("#username", username)
        await page.fill("#password", password)
        
        # Fast submit
        await page.click("#kc-login")
        
        # 6. Check for immediate error messages
        try:
            await page.wait_for_selector(".alert-error, .kc-feedback-text, .main-sidebar, .user-panel", timeout=10000)
            if await page.query_selector(".alert-error, .kc-feedback-text"):
                err_text = "Username atau password salah (SSO)"
                err_el = await page.query_selector(".kc-feedback-text")
                if err_el: err_text = await err_el.inner_text()
                print(f"   ❌ [Auth] Login failed: {err_text}")
                return False, err_text
        except:
            pass

        return True, None

    except Exception as e:
        print(f"❌ [Auth] Error in perform_sso_login: {e}")
        return False, str(e)

async def auto_login(page, username, password):
    """
    Robust login flow for RPA workers.
    """
    try:
        print(f"🚀 [Auth] Starting automated login for {username}...")
        
        # 1. Start from Target App (SSO will trigger automatically)
        success, err_msg = await perform_sso_login(page, username, password)
        if not success:
            return False, {}, err_msg
            
        # 2. Wait for landing on the target app
        print("   ⏳ [Auth] Waiting for redirect to FASIH-SM...")
        try:
            # Wait for elements that signify a successful login in FASIH-SM
            await page.wait_for_selector(".main-sidebar, .user-panel, a[href*='logout'], .navbar", timeout=60000)
            print("   ✅ [Auth] Dashboard detected!")
        except Exception:
            # If not detected, check if we are at least on the domain
            if "fasih-sm.bps.go.id" in page.url:
                print(f"   ℹ️ [Auth] On target domain but sidebar missing. Proceeding.")
            else:
                return False, {}, "Dashboard tidak terjangkau setelah SSO"
        
        # 3. Capture cookies
        cookies_list = await page.context.cookies()
        cookies_dict = {c['name']: c['value'] for c in cookies_list}
        
        # Check critical session cookies
        has_session = any(name in cookies_dict for name in ['XSRF-TOKEN', 'laravel_session'])
        if has_session:
            print(f"✅ [Auth] Session captured ({len(cookies_dict)} cookies).")
            return True, cookies_dict, None
        else:
            return False, {}, "Missing session cookies"
            
    except Exception as e:
        print(f"❌ [Auth] auto_login failed: {e}")
        return False, {}, str(e)

async def fetch_vpn_cookie(username, password):
    """
    Automate flow for VPN container. Returns the raw SVPNCOOKIE value.
    """
    browser = None
    try:
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(browser)
            page = await context.new_page()
            
            success, err_msg = await perform_sso_login(page, username, password, target_url="https://akses.bps.go.id/remote/login")
            if not success:
                print(f"❌ [Auth] Failed to login to VPN portal: {err_msg}")
                await browser.close()
                return None
            
            # Polling for SVPNCOOKIE
            print(f"🚀 [Auth] Polling for SVPNCOOKIE (max 90s)...")
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 90:
                cookies = await context.cookies()
                vpn_cookie = next((c['value'] for c in cookies if c['name'] == 'SVPNCOOKIE'), None)
                if vpn_cookie:
                    print(f"✅ [Auth] SVPNCOOKIE found.")
                    await browser.close()
                    return vpn_cookie
                await asyncio.sleep(2)
            
            await browser.close()
            return None
    except Exception as e:
        print(f"❌ [Auth] Error in fetch_vpn_cookie: {e}")
        if browser: await browser.close()
        return None

async def sync_cookie_to_db(cookie):
    """Save the fresh cookie to the system_settings table."""
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO system_settings (key, value) VALUES ('vpn_cookie', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (cookie,)
        )
        conn.commit()
        cur.close()
        conn.close()
        print("✅ [Auth] Cookie successfully synchronized to database.")
        return True
    except Exception as e:
        print(f"❌ [Auth] Database sync failed: {e}")
        return False

async def new_stealth_context(browser, **kwargs):
    """Legacy wrapper for creating a stealth context with merged options."""
    defaults = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {'width': 1280, 'height': 800},
        "is_mobile": False,
        "has_touch": False,
        "locale": "en-US",
        "timezone_id": "Asia/Jakarta"
    }
    options = {**defaults, **kwargs}
    return await browser.new_context(**options)
