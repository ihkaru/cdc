"""
Detail Page — Concurrent API Fetch untuk data assignment

Supports both serial (via Playwright page.evaluate) and concurrent (via aiohttp)
fetching strategies. Concurrent mode uses cookies from the Playwright session
to make parallel HTTP requests with asyncio.Semaphore for rate-limiting.
"""

import asyncio
import os
import re
import ssl

from api_client import FasihAuthError

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
API_BASE = f"{TARGET_URL}/app/api/assignment-general/api/assignment/get-by-assignment-id"
MAX_RETRIES = 3
RETRY_DELAY = 0.3  # seconds — flat delay, not exponential (VPN latency ~5s already penalizes enough)


def extract_assignment_id(detail_url: str) -> str | None:
    """
    Ekstrak Assignment ID dari URL detail.
    Contoh: /survey-collection/assignment-detail/{ASSIGNMENT_ID}/{SURVEY_ID}
    """
    match = re.search(r"/assignment-detail/([a-f0-9\-]+)/", detail_url)
    if match:
        return match.group(1)
    return None


async def fetch_assignment_data(page, detail_url: str) -> dict | None:
    """
    Panggil API JSON langsung dari browser context via fetch().
    Memanfaatkan cookies session yang sudah aktif.

    Dengan retry logic: coba hingga MAX_RETRIES kali jika gagal.

    Returns:
        dict data assignment, atau None jika gagal
    """
    assignment_id = extract_assignment_id(detail_url)
    if not assignment_id:
        print(f"   ⚠️ Gagal parse Assignment ID dari: {detail_url}")
        return None

    api_url = f"{API_BASE}?id={assignment_id}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await page.evaluate(
                """async (apiUrl) => {
                try {
                    const response = await fetch(apiUrl, {
                        method: 'GET',
                        credentials: 'include',
                        headers: { 'Accept': 'application/json' }
                    });
                    if (!response.ok) {
                        return { error: true, status: response.status, message: response.statusText };
                    }
                    const json = await response.json();
                    return json;
                } catch (e) {
                    return { error: true, message: e.toString() };
                }
            }""",
                api_url,
            )

            if result and result.get("success"):
                return result.get("data", {})

            error_msg = result.get("message", "Unknown") if result else "No response"

            if attempt < MAX_RETRIES:
                print(f"   ⚠️ Attempt {attempt}/{MAX_RETRIES} gagal ({error_msg}), retry in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print(f"   ❌ Gagal setelah {MAX_RETRIES}x: {assignment_id[:8]}... ({error_msg})")
                return None

        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"   ⚠️ Attempt {attempt}/{MAX_RETRIES} exception: {e}, retry...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print(f"   ❌ Exception setelah {MAX_RETRIES}x: {e}")
                return None

    return None


# =====================================================================
# Concurrent Fetcher — uses aiohttp with cookies from Playwright
# =====================================================================


async def extract_cookies_from_context(context) -> dict:
    """Extract cookies from Playwright browser context as a dict for aiohttp."""
    cookies = await context.cookies()
    return {c["name"]: c["value"] for c in cookies}


async def _fetch_one(
    session,
    assignment_id: str,
    semaphore: asyncio.Semaphore,
    headers: dict = None,
    retries: int = MAX_RETRIES,
) -> dict | None:
    """Fetch a single assignment detail via aiohttp with retry and semaphore."""
    import aiohttp

    api_url = f"{API_BASE}?assignmentId={assignment_id}"

    async with semaphore:
        for attempt in range(1, retries + 1):
            if session.closed:
                return None
            try:
                async with session.get(
                    api_url,
                    headers=headers or {"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    # [Scenario 2 Fix] Explicitly detect BPS SSO Redirects
                    if "oauth_login" in str(resp.url) or "sso.bps.go.id" in str(resp.url):
                        raise FasihAuthError("Session expired: redirected to SSO login")

                    if resp.status != 200:
                        body_text = await resp.text()
                        print(f"   ❌ {assignment_id[:8]}... HTTP {resp.status}: {body_text[:100]}")
                        if resp.status in (401, 403, 404):
                            return None
                        if attempt < retries:
                            if session.closed:
                                return None
                            await asyncio.sleep(RETRY_DELAY)  # flat delay — not exponential
                            continue
                        return None

                    # Guard: BPS returns HTTP 200 + HTML (login page) when cookie expires mid-fetch.
                    content_type = resp.headers.get("content-type", "")
                    if "text/html" in content_type:
                        body_text = await resp.text()
                        if "login" in body_text[:500].lower() or "<html" in body_text[:200].lower():
                            raise FasihAuthError("Session expired mid-fetch: returned HTML login page")
                        print(f"   ❌ {assignment_id[:8]}... Unexpected HTML response (not login page).")
                        return None

                    try:
                        import orjson

                        body = await resp.json(loads=orjson.loads)
                    except ImportError:
                        body = await resp.json()
                    if body and body.get("success"):
                        return body.get("data", {})

                    print(f"   ❌ {assignment_id[:8]}... API returned success=False: {body}")

                    if attempt < retries:
                        if session.closed:
                            return None
                        await asyncio.sleep(RETRY_DELAY)  # flat delay
                        continue
                    else:
                        return None

            except FasihAuthError as e:
                print(f"   🚨 {assignment_id[:8]}... FasihAuthError: {e}")
                raise
            except Exception as e:
                if session.closed:
                    return None
                # Print type+repr so empty-message exceptions (TimeoutError, ServerDisconnectedError) are visible
                print(f"   ❌ {assignment_id[:8]}... {type(e).__name__}: {e!r}")
                if attempt < retries:
                    await asyncio.sleep(RETRY_DELAY)  # flat delay
                else:
                    return None

    return None


async def _relogin_headless(username: str, password: str) -> dict | None:
    """
    Lakukan headless re-login via Playwright dan kembalikan cookie dict baru.
    Dipanggil saat session expired mid-fetch untuk resume operasi.
    """
    try:
        from playwright.async_api import async_playwright

        from auth import auto_login, launch_stealth_browser, new_stealth_context

        print("   🔄 [ReLogin] Session expired mid-fetch. Memulai headless re-login...")
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(browser)
            try:
                page = await context.new_page()
                ok, new_cookies, err = await auto_login(page, username, password)
                if ok and new_cookies:
                    print(f"   ✅ [ReLogin] Re-login berhasil ({len(new_cookies)} cookies). Melanjutkan fetch...")
                    return new_cookies
                else:
                    print(f"   ❌ [ReLogin] Re-login gagal: {err}")
                    return None
            finally:
                await browser.close()
    except Exception as e:
        print(f"   ❌ [ReLogin] Exception saat re-login: {e}")
        return None


async def fetch_assignments_concurrent(
    cookie_dict: dict,
    urls: list[str],
    concurrency: int = 5,
    on_progress=None,
    sso_username: str = "",
    sso_password: str = "",
) -> list[dict]:
    """
    Fetch multiple assignment details concurrently using aiohttp with a true
    Producer-Consumer Pipeline (asyncio.Queue) to overlap fetch and write,
    supported by a dynamic multi-session round-robin pool of valid administrators.
    """
    import json
    from urllib.parse import unquote

    import aiohttp

    from api_client import FasihApiClient
    from db.connection import get_session
    from db.models import SystemSettings

    # Create SSL context that doesn't verify (VPN internal network)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # Parse assignment IDs from URLs
    id_map = []
    for url in urls:
        aid = extract_assignment_id(url)
        if aid:
            id_map.append(aid)

    if not id_map:
        return []

    # 1. Dynamically load all active sessions from the database
    all_sessions = []

    def parse_session_cookies(val_str):
        try:
            val = json.loads(val_str)
            if isinstance(val, dict) and "cookies" in val:
                return {c["name"]: c["value"] for c in val["cookies"]}
            elif isinstance(val, dict):
                return val
        except Exception:
            pass
        return None

    # Insert primary session first
    if cookie_dict and "SESSION" in cookie_dict:
        all_sessions.append(cookie_dict)

    # Load other admin sessions
    try:
        db_sess = get_session()
        records = db_sess.query(SystemSettings).filter(SystemSettings.key.like("sso_state_%")).all()
        for rec in records:
            cookies = parse_session_cookies(rec.value)
            if cookies and "SESSION" in cookies:
                sess_val = cookies.get("SESSION")
                if sess_val and not any(s.get("SESSION") == sess_val for s in all_sessions):
                    all_sessions.append(cookies)
        db_sess.close()
    except Exception as db_err:
        print(f"   ⚠️ Failed loading multi-session cookies from DB: {db_err}")

    # Fallback if empty
    if not all_sessions and cookie_dict:
        all_sessions.append(cookie_dict)

    # 2. Concurrently validate which sessions are active/valid (timeout 5s per validation)
    async def validate_session(c_dict) -> bool:
        probe_url = f"{TARGET_URL}/survey/api/v1/users/myinfo"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
            "X-XSRF-TOKEN": unquote(c_dict.get("XSRF-TOKEN", "")),
        }
        try:
            # Short-lived check connection context
            # Timeout 12s: BPS VPN latency regularly exceeds 5s — old timeout caused false-negative rejections
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            async with aiohttp.ClientSession(cookies=c_dict, connector=connector) as test_sess:
                async with test_sess.get(probe_url, headers=headers, timeout=12) as test_resp:
                    # Expired session will redirect to Keycloak/SSO
                    if "oauth_login" in str(test_resp.url) or "sso.bps.go.id" in str(test_resp.url):
                        return False

                    # BPS Fortinet returns HTTP 200 with HTML body (login page) on expired cookies.
                    content_type = test_resp.headers.get("content-type", "")
                    body_text = await test_resp.text()
                    is_html_response = (
                        "text/html" in content_type
                        or body_text.lstrip().startswith("<!")
                        or ("login" in body_text.lower() and "<html" in body_text.lower())
                    )
                    if test_resp.status == 200 and not is_html_response:
                        return True
                    else:
                        if is_html_response:
                            print("   ⚠️ Session rejected: returned HTML login page (cookie expired).")
                        return False
        except Exception:
            return False

    print(f"   👥 Found {len(all_sessions)} candidates in dynamic session pool. Validating active states...")
    validation_tasks = [validate_session(s) for s in all_sessions]
    validation_results = await asyncio.gather(*validation_tasks)

    validated_sessions = [all_sessions[i] for i, is_valid in enumerate(validation_results) if is_valid]

    # Ensure we have at least one session; if validation aggressively filtered all, fallback to primary
    if not validated_sessions:
        print("   ⚠️ All sessions failed validation. Falling back to primary session...")
        validated_sessions = [cookie_dict]
    else:
        print(f"   ✓ Session pool loaded: {len(validated_sessions)} active administrative session(s).")

    # 3. Setup client contexts for all validated sessions
    clients_pool = []
    for c_dict in validated_sessions:
        api_client = FasihApiClient(c_dict)
        api_client.ssl_ctx = ssl_ctx

        # We configure the underlying session with connector limits
        connector = aiohttp.TCPConnector(
            ssl=ssl_ctx,
            limit=concurrency + 10,
            limit_per_host=concurrency,
            keepalive_timeout=120,
            force_close=False,
        )

        api_client._session = aiohttp.ClientSession(
            cookie_jar=api_client.jar,
            headers=api_client._get_headers(),
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=45, connect=15),
        )
        clients_pool.append(api_client)

    print(f"   🚀 Fetching {len(id_map)} assignments with concurrency={concurrency} (Overlap Pipeline)...")

    semaphore = asyncio.Semaphore(concurrency)
    results = []
    total = len(id_map)
    completed_count = 0

    # ---------------------------------------------------------------
    # Resilient Batch Runner
    # Runs assignments in batches. Jika session expired mid-batch,
    # re-login dilakukan dan sisa assignment dilanjutkan dengan
    # session baru. Tidak ada early-abort.
    # ---------------------------------------------------------------
    MAX_RELOGIN_ATTEMPTS = 3

    async def _run_batch(current_pool: list, batch_ids: list[str]) -> tuple[list[str], bool]:
        """
        Jalankan satu batch. Returns (failed_ids, had_auth_error).
        failed_ids berisi ID yang belum sempat diproses karena auth error.
        """
        nonlocal completed_count

        queue = asyncio.Queue(maxsize=concurrency * 2)
        failed_ids = []
        had_auth_error = False
        auth_error_aid = None

        async def producer_task(client_session, aid, headers_dict):
            try:
                data = await _fetch_one(client_session, aid, semaphore, headers=headers_dict)
                await queue.put((aid, data))
                return True
            except FasihAuthError:
                await queue.put((aid, FasihAuthError("Session expired")))
                raise
            except Exception as e:
                print(f"   ⚠️ Producer Error for {aid[:8]}: {e}")
                await queue.put((aid, None))
                return False

        async def consumer_task():
            nonlocal completed_count, had_auth_error, auth_error_aid
            while True:
                item = await queue.get()
                if item is None:  # Sentinel for completion
                    queue.task_done()
                    break

                aid, data = item

                if isinstance(data, FasihAuthError):
                    # Auth error detected — stop consuming, remainder will be tracked
                    had_auth_error = True
                    auth_error_aid = aid
                    queue.task_done()
                    break

                completed_count += 1

                if not on_progress and data:
                    results.append(data)

                if on_progress:
                    try:
                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(completed_count, total, data)
                        else:
                            on_progress(completed_count, total, data)
                    except Exception as cb_err:
                        print(f"   ⚠️ Callback Error: {cb_err}")

                if not on_progress and (completed_count % 100 == 0 or completed_count == total):
                    print(f"   📊 Progress: {completed_count}/{total}")

                queue.task_done()

        c_task = asyncio.create_task(consumer_task())

        p_tasks = []
        for idx, aid in enumerate(batch_ids):
            client_instance = current_pool[idx % len(current_pool)]
            session = client_instance.session
            headers = client_instance._get_headers()
            p_tasks.append(asyncio.create_task(producer_task(session, aid, headers)))

        cancelled_ids = []
        try:
            await asyncio.gather(*p_tasks)
        except FasihAuthError:
            # Auth error raised — cancel all remaining producers and collect unstarted IDs
            still_pending = []
            for idx, t in enumerate(p_tasks):
                if not t.done():
                    t.cancel()
                    still_pending.append(batch_ids[idx])
            cancelled_ids = still_pending
            print(
                f"   ⚠️ [Resilient] Auth error detected. {len(cancelled_ids)} sisa assignment akan di-resume setelah re-login."
            )
        finally:
            await queue.put(None)  # Signal consumer
            await c_task

        # Collect all IDs that were not successfully fetched
        if had_auth_error:
            failed_ids = cancelled_ids
            # Also include the ID that triggered the auth error if it wasn't fetched
            if auth_error_aid and auth_error_aid not in failed_ids:
                failed_ids.insert(0, auth_error_aid)

        return failed_ids, had_auth_error

    async def run_pipeline():
        remaining_ids = list(id_map)
        current_pool = list(clients_pool)
        relogin_attempts = 0

        while remaining_ids:
            failed_ids, had_auth_error = await _run_batch(current_pool, remaining_ids)

            if not had_auth_error:
                # Semua berhasil (atau gagal bukan karena auth)
                break

            # Auth error → coba re-login jika credentials tersedia
            if not sso_username or not sso_password:
                print(
                    "   ❌ [Resilient] Session expired tapi credentials tidak tersedia untuk re-login. "
                    f"{len(failed_ids)} assignment tidak terambil."
                )
                break

            relogin_attempts += 1
            if relogin_attempts > MAX_RELOGIN_ATTEMPTS:
                print(
                    f"   ❌ [Resilient] Sudah {MAX_RELOGIN_ATTEMPTS}x re-login tapi session terus expired. "
                    f"Menghentikan. {len(failed_ids)} assignment tidak terambil."
                )
                break

            print(f"   🔄 [Resilient] Re-login attempt {relogin_attempts}/{MAX_RELOGIN_ATTEMPTS}...")
            new_cookies = await _relogin_headless(sso_username, sso_password)
            if not new_cookies:
                print(f"   ❌ [Resilient] Re-login gagal. {len(failed_ids)} assignment tidak terambil.")
                break

            # Rebuild client pool dengan session baru
            # Tutup pool lama terlebih dahulu
            for old_client in current_pool:
                try:
                    if old_client._session and not old_client._session.closed:
                        await old_client._session.close()
                except Exception:
                    pass

            new_client = FasihApiClient(new_cookies)
            new_client.ssl_ctx = ssl_ctx
            connector = aiohttp.TCPConnector(
                ssl=ssl_ctx,
                limit=concurrency + 10,
                limit_per_host=concurrency,
                keepalive_timeout=120,
                force_close=False,
            )
            new_client._session = aiohttp.ClientSession(
                cookie_jar=new_client.jar,
                headers=new_client._get_headers(),
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=45, connect=15),
            )
            # Enter context manually
            await new_client.__aenter__()
            current_pool = [new_client]
            remaining_ids = failed_ids
            print(f"   ✅ [Resilient] Session baru aktif. Melanjutkan {len(remaining_ids)} assignment...")

    # Enter context for all initially-validated clients, then run pipeline
    async def enter_client_context(index):
        if index >= len(clients_pool):
            await run_pipeline()
            return
        async with clients_pool[index] as _:
            await enter_client_context(index + 1)

    await enter_client_context(0)

    print(f"   ✅ Done: {len(results) if not on_progress else 'Streamed'} processed")
    return results
