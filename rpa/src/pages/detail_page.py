"""
Detail Page — Concurrent API Fetch untuk data assignment

Supports both serial (via Playwright page.evaluate) and concurrent (via aiohttp)
fetching strategies. Concurrent mode uses cookies from the Playwright session
to make parallel HTTP requests with asyncio.Semaphore for rate-limiting.
"""
import os
import re
import json
import asyncio
import ssl
from typing import Optional

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
API_BASE = f"{TARGET_URL}/assignment-general/api/assignment/get-by-id-with-data-for-scm"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def extract_assignment_id(detail_url: str) -> str | None:
    """
    Ekstrak Assignment ID dari URL detail.
    Contoh: /survey-collection/assignment-detail/{ASSIGNMENT_ID}/{SURVEY_ID}
    """
    match = re.search(r'/assignment-detail/([a-f0-9\-]+)/', detail_url)
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
            result = await page.evaluate('''async (apiUrl) => {
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
            }''', api_url)

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
    retries: int = MAX_RETRIES,
) -> Optional[dict]:
    """Fetch a single assignment detail via aiohttp with retry and semaphore."""
    import aiohttp
    api_url = f"{API_BASE}?id={assignment_id}"

    async with semaphore:
        for attempt in range(1, retries + 1):
            try:
                async with session.get(
                    api_url,
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        body_text = await resp.text()
                        print(f"   ❌ {assignment_id[:8]}... HTTP {resp.status}: {body_text[:100]}")
                        if attempt < retries:
                            await asyncio.sleep(RETRY_DELAY * attempt)
                            continue
                        return None

                    body = await resp.json()
                    if body and body.get("success"):
                        return body.get("data", {})
                    
                    print(f"   ❌ {assignment_id[:8]}... API returned success=False: {body}")

                    if attempt < retries:
                        await asyncio.sleep(RETRY_DELAY * attempt)
                        continue
                    else:
                        return None

            except Exception as e:
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
    
    # Use a cookie jar with the extracted cookies
    jar = aiohttp.CookieJar(unsafe=True)
    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=concurrency + 5)

    async with aiohttp.ClientSession(
        cookies=cookie_dict,
        cookie_jar=jar,
        connector=connector,
    ) as session:
        tasks = []
        for aid in id_map:
            tasks.append(_fetch_one(session, aid, semaphore))

        for coro in asyncio.as_completed(tasks):
            data = await coro
            completed += 1

            if data:
                results.append(data)

            if on_progress:
                on_progress(completed, total, data)
            elif completed % 100 == 0 or completed == total:
                success_rate = len(results) / completed * 100 if completed > 0 else 0
                print(f"   📊 Progress: {completed}/{total} ({success_rate:.0f}% success)")

    print(f"   ✅ Done: {len(results)}/{total} fetched successfully")
    return results
