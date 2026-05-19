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
API_BASE = f"{TARGET_URL}/assignment-general/api/assignment/get-by-id-with-data-for-scm"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


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

    api_url = f"{API_BASE}?id={assignment_id}"

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
                            await asyncio.sleep(RETRY_DELAY * attempt)
                            continue
                        return None

                    body = await resp.json()
                    if body and body.get("success"):
                        return body.get("data", {})

                    print(f"   ❌ {assignment_id[:8]}... API returned success=False: {body}")

                    if attempt < retries:
                        if session.closed:
                            return None
                        await asyncio.sleep(RETRY_DELAY * attempt)
                        continue
                    else:
                        return None

            except FasihAuthError as e:
                print(f"   🚨 {assignment_id[:8]}... FasihAuthError: {e}")
                raise
            except Exception as e:
                if session.closed:
                    return None
                print(f"   ❌ {assignment_id[:8]}... Exception: {e}")
                if attempt < retries:
                    await asyncio.sleep(RETRY_DELAY * attempt)
                else:
                    return None

    return None


async def fetch_assignments_concurrent(
    cookie_dict: dict,
    urls: list[str],
    concurrency: int = 5,
    on_progress=None,
) -> list[dict]:
    """
    Fetch multiple assignment details concurrently using aiohttp.

    Args:
        cookie_dict: Dictionary of session cookies
        urls: List of assignment detail URLs
        concurrency: Maximum number of concurrent requests
        on_progress: Optional callback(fetched_count, total_count, data_or_none)

    Returns:
        List of successfully fetched assignment data dicts
    """
    import aiohttp

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

    print(f"   🚀 Fetching {len(id_map)} assignments with concurrency={concurrency}...")

    semaphore = asyncio.Semaphore(concurrency)
    results = []
    completed = 0
    total = len(id_map)

    # Re-use enterprise-grade FasihApiClient to boot session with yarl-cookie domains
    from api_client import FasihApiClient

    api_client = FasihApiClient(cookie_dict)
    api_client.ssl_ctx = ssl_ctx

    # We dynamically configure the underlying session with concurrency connector limits
    connector = aiohttp.TCPConnector(
        ssl=ssl_ctx,
        limit=concurrency + 10,
        limit_per_host=concurrency,
        keepalive_timeout=60,
        force_close=False,
    )

    # Instantiate custom session inside client with custom connector
    api_client._session = aiohttp.ClientSession(
        cookie_jar=api_client.jar,
        headers=api_client._get_headers(),
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=45, connect=15),
    )

    async with api_client as client:
        session = client.session
        headers = client._get_headers()

        tasks = []
        for aid in id_map:
            tasks.append(asyncio.create_task(_fetch_one(session, aid, semaphore, headers=headers)))

        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    data = await coro
                    completed += 1

                    # Memory optimization: if on_progress (callback) is provided,
                    # we don't need to store all results in memory here.
                    # The caller handles the storage (e.g. BatchUpserterBulk).
                    if not on_progress and data:
                        results.append(data)

                    if on_progress:
                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(completed, total, data)
                        else:
                            on_progress(completed, total, data)
                    elif completed % 100 == 0 or completed == total:
                        # Fallback logging if no callback
                        print(f"   📊 Progress: {completed}/{total}")
                except FasihAuthError:
                    print(
                        "   🚨 [Early-Abort] Ditemukan FasihAuthError (session expired)! Menghentikan semua sisa request..."
                    )
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    raise
        except FasihAuthError:
            raise

    print(f"   ✅ Done: {completed}/{total} processed")
    return results
