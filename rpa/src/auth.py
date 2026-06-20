import asyncio
import os

import psycopg2
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
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-http2",  # Critical: BPS Portal handles HTTP/1.1 better
        ],
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
                await page.goto(target_url, wait_until="commit", timeout=120000)

                # Apply 5-Second Stabilization Rule specifically for VPN Portal (akses.bps.go.id)
                if "akses.bps.go.id" in target_url:
                    print("   ⏳ [Auth] Waiting 5s for VPN Portal background scripts to stabilize...")
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)

            # 3. Wait for SAML Button or FASIH-SM SSO Selection
            print("🚀 [Auth] Detecting SSO/SAML login button...")
            saml_selectors = [
                "#saml-login-bn",
                ".btn-saml",
                "button:has-text('Login SSO')",
                "button:has-text('SAML')",
                "a[href*='/oauth2/authorization/ics']",
                "a:has-text('Login SSO BPS')",
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
        print(f"🚀 [Auth] Waiting for Keycloak SSO redirection... Current URL: {page.url}", flush=True)
        try:
            # wait_until="commit" ensures we don't wait 20s+ for fonts to load on Keycloak
            await page.wait_for_url(lambda url: "sso.bps.go.id" in url, timeout=45000, wait_until="commit")
            print(f"   ✅ [Auth] Keycloak SSO URL reached: {page.url}", flush=True)
        except Exception as e:
            print(f"   ❌ [Auth] Timeout waiting for SSO redirect. Stuck at URL: {page.url}", flush=True)
            return False, f"Gagal dialihkan ke SSO: {e!s}"

        try:
            # Wait for the username input field to be ready in DOM
            await page.wait_for_selector("#username", timeout=30000)
            print("   ✅ [Auth] SSO username field is ready.", flush=True)
        except Exception:
            print(f"   ❌ [Auth] #username field not found. URL: {page.url}", flush=True)
            return False, f"Berada di SSO tapi #username tidak ditemukan. URL: {page.url}"

        # 5. Fill Credentials using direct JS injection (Bypass UI stalling)
        print("🚀 [Auth] Injecting credentials via JS...")
        await page.evaluate(f"""() => {{
            const userField = document.querySelector('#username');
            const passField = document.querySelector('#password');
            if (userField) userField.value = '{username}';
            if (passField) passField.value = '{password}';
        }}""")

        # Fast submit and wait for navigation commit
        try:
            async with page.expect_navigation(wait_until="commit", timeout=45000):
                await page.click("#kc-login", force=True)
        except Exception as e:
            return False, f"Timeout saat mensubmit form login SSO: {e!s}"

        # 6. Check resulting URL to determine success.
        # wait_until="commit" fires on the FIRST http response (including 302 redirects),
        # so page.url may still be sso.bps.go.id even on a successful login for portals
        # like akses.bps.go.id that have a multi-step redirect chain.
        # Screenshot evidence shows FortiGate SAML redirect takes >5s — raise to 30s.
        if "sso.bps.go.id" in page.url:
            try:
                await page.wait_for_url(lambda url: "sso.bps.go.id" not in url, timeout=30000, wait_until="commit")
                # URL changed — login succeeded
                print("   ✅ [Auth] Login berhasil diterima Keycloak, beralih ke aplikasi...", flush=True)
                return True, None
            except Exception:
                # Still on sso.bps.go.id after 30s → genuine login failure
                print("   ❌ [Auth] Login ditolak. URL masih di SSO BPS setelah 30s.", flush=True)
                try:
                    await page.wait_for_selector(".alert-error, .kc-feedback-text", timeout=5000)
                    err_text = "Username atau password salah (SSO)"
                    err_el = await page.query_selector(".kc-feedback-text")
                    if err_el:
                        err_text = await err_el.inner_text()
                    print(f"   ❌ [Auth] Detail error: {err_text}")
                    return False, err_text
                except Exception:
                    return False, "Username atau password salah (SSO BPS)"

        print("   ✅ [Auth] Login berhasil diterima Keycloak, beralih ke aplikasi...", flush=True)
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

        # 📸 Start Tracing on the page context if it hasn't been started
        context = page.context
        os.makedirs("/app/traces", exist_ok=True)
        try:
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        except Exception:
            pass  # Already tracing or not supported

        # 1. Start from Target App (SSO will trigger automatically)
        success, err_msg = await perform_sso_login(page, username, password)
        if not success:
            # 📸 Capture failure screenshot and trace
            try:
                await page.screenshot(path="/app/traces/sso_error.png", timeout=5000)
                await context.tracing.stop(path="/app/traces/sso_trace.zip")
                print("📸 [Auth] Login failed. Error screenshot and trace saved to /app/traces/")
            except Exception as se:
                print(f"⚠️ [Auth] Could not save failure trace/screenshot: {se}")
            return False, {}, err_msg

        # 2. Poll for session cookies (max 30s) to bypass slow asset loads/rendering
        print("   ⏳ [Auth] Polling for FASIH-SM session cookies (max 30s)...")
        start_time = asyncio.get_event_loop().time()
        cookies_dict = {}
        has_session = False
        while (asyncio.get_event_loop().time() - start_time) < 30:
            cookies_list = await page.context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in cookies_list}
            has_session = any(name in cookies_dict for name in ["XSRF-TOKEN", "laravel_session"])
            if has_session:
                print(f"   ✅ [Auth] Session captured early ({len(cookies_dict)} cookies) via polling.")
                break
            await asyncio.sleep(2)

        # Fallback: if polling failed, wait for elements (but with a short 15s timeout)
        if not has_session:
            print("   ⏳ [Auth] Session cookies not found in polling. Waiting for landing element (max 15s)...")
            try:
                await page.wait_for_selector(".main-sidebar, .user-panel, a[href*='logout'], .navbar", timeout=15000)
                print("   ✅ [Auth] Dashboard detected!")
                cookies_list = await page.context.cookies()
                cookies_dict = {c["name"]: c["value"] for c in cookies_list}
                has_session = any(name in cookies_dict for name in ["XSRF-TOKEN", "laravel_session"])
            except Exception as e:
                # 📸 Capture failure screenshot and trace with short timeout
                try:
                    await page.screenshot(path="/app/traces/sso_error.png", timeout=5000)
                    await context.tracing.stop(path="/app/traces/sso_trace.zip")
                    print("📸 [Auth] Timeout waiting for Dashboard. Error screenshot and trace saved.")
                except Exception as se:
                    print(f"⚠️ [Auth] Could not save timeout trace/screenshot: {se}")

                if "fasih-sm.bps.go.id" in page.url:
                    print("   ℹ️ [Auth] On target domain but sidebar missing. Proceeding.")
                    cookies_list = await page.context.cookies()
                    cookies_dict = {c["name"]: c["value"] for c in cookies_list}
                    has_session = any(name in cookies_dict for name in ["XSRF-TOKEN", "laravel_session"])
                else:
                    return False, {}, f"Dashboard tidak terjangkau setelah SSO: {e!s}"

        if has_session:
            print(f"✅ [Auth] Session captured ({len(cookies_dict)} cookies).")
            # Clean up tracing on success without saving to save space
            try:
                await context.tracing.stop()
            except:
                pass
            return True, cookies_dict, None
        else:
            # 📸 Capture screenshot on missing session cookies
            try:
                await page.screenshot(path="/app/traces/sso_error.png", timeout=5000)
                await context.tracing.stop(path="/app/traces/sso_trace.zip")
            except:
                pass
            return False, {}, "Missing session cookies"

    except Exception as e:
        print(f"❌ [Auth] auto_login failed: {e}")
        try:
            await page.screenshot(path="/app/traces/sso_error.png", timeout=5000)
            await page.context.tracing.stop(path="/app/traces/sso_trace.zip")
        except:
            pass
        return False, {}, str(e)


async def fetch_vpn_cookie(username, password):
    """
    Automate flow for VPN container. Returns the raw SVPNCOOKIE value.
    """
    browser = None
    context = None
    try:
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(browser)

            # 📸 Enable Playwright Tracing
            os.makedirs("/app/traces", exist_ok=True)
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = await context.new_page()

            success, err_msg = await perform_sso_login(
                page, username, password, target_url="https://akses.bps.go.id/remote/login"
            )
            if not success:
                print(f"❌ [Auth] Failed to login to VPN portal: {err_msg}")
                # 📸 Capture failure screenshot and trace
                try:
                    await page.screenshot(path="/app/traces/sso_error.png", timeout=5000)
                    await context.tracing.stop(path="/app/traces/sso_trace.zip")
                    print("📸 [Auth] Error screenshot and trace saved to /app/traces/")
                except Exception as se:
                    print(f"⚠️ [Auth] Could not save failure screenshot: {se}")
                await browser.close()
                return None

            # Polling for SVPNCOOKIE
            print("🚀 [Auth] Polling for SVPNCOOKIE (max 90s)...")
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 90:
                cookies = await context.cookies()
                vpn_cookie = next((c["value"] for c in cookies if c["name"] == "SVPNCOOKIE"), None)
                if vpn_cookie:
                    print("✅ [Auth] SVPNCOOKIE found.")
                    # Clean up tracing on success without saving to save space
                    try:
                        await context.tracing.stop()
                    except:
                        pass
                    await browser.close()
                    return vpn_cookie
                await asyncio.sleep(2)

            # 📸 Capture screenshot on timeout
            try:
                await page.screenshot(path="/app/traces/sso_error.png", timeout=5000)
                await context.tracing.stop(path="/app/traces/sso_trace.zip")
                print("📸 [Auth] Timeout. Error screenshot and trace saved to /app/traces/")
            except Exception as se:
                print(f"⚠️ [Auth] Could not save timeout screenshot: {se}")
            await browser.close()
            return None
    except Exception as e:
        print(f"❌ [Auth] Error in fetch_vpn_cookie: {e}")
        if context:
            try:
                await context.tracing.stop(path="/app/traces/sso_trace.zip")
            except:
                pass
        if browser:
            await browser.close()
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
            (cookie,),
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
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "viewport": {"width": 360, "height": 640},
        "is_mobile": True,
        "has_touch": True,
        "locale": "en-US",
        "timezone_id": "Asia/Jakarta",
    }
    options = {**defaults, **kwargs}
    return await browser.new_context(**options)
