#!/usr/bin/env python
"""
test_multisession_perf.py — Verification benchmark for Multi-Session Round-Robin.
Loads all active sso_state_% settings and performs high-concurrency requests distributed across them.
"""

import asyncio
import json
import os
import sys
import time
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import get_session, get_session_factory
from db.models import Assignment, SystemSettings
from db.repository import BatchUpserterBulk

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
CAPI_API_BASE = f"{TARGET_URL}/app/api/assignment-general/api/assignment/get-by-assignment-id"


def print_banner():
    print("=" * 90)
    print("      👥  FasihNexus — Multi-Session Session Pool Concurrency Experiment  👥      ")
    print("=" * 90)


def parse_cookies(val_str):
    try:
        val = json.loads(val_str)
        if isinstance(val, dict) and "cookies" in val:
            return {c["name"]: c["value"] for c in val["cookies"]}
        elif isinstance(val, dict):
            return val
    except Exception as e:
        print(f"   ⚠️ Error parsing cookies: {e}")
    return {}


async def producer(session, aid, survey_config_id, queue, semaphore, headers):
    """Producer coroutine: fetches detail data and puts it into the queue."""
    url = f"{CAPI_API_BASE}?assignmentId={aid}"
    async with semaphore:
        try:
            async with session.get(url, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    import orjson

                    body = await resp.json(loads=orjson.loads)
                    if body and body.get("success"):
                        data = body.get("data")
                        if data:
                            data["_survey_config_id"] = str(survey_config_id) if survey_config_id else None
                            await queue.put(data)
                            return True
                elif resp.status == 403:
                    # Print 403 details as it helps diagnose auth scopes
                    pass
        except Exception:
            pass
    return False


async def consumer(queue, db_session_factory, stats):
    """Consumer coroutine: reads from the queue and writes to the DB in batches."""
    session = db_session_factory()
    upserter = BatchUpserterBulk(session, batch_size=50)
    processed = 0

    try:
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break
            upserter.add(item)
            processed += 1
            queue.task_done()

        if upserter._buffer:
            upserter.flush()
    except Exception as e:
        print(f"❌ Consumer Error: {e}")
    finally:
        session.commit()
        session.close()
        stats["success_count"] = upserter.stats.total_fetched - upserter.stats.total_failed


async def main():
    print_banner()

    # 1. Retrieve all active admin cookies
    print("[1] Querying all active sessions from system_settings...")
    db_session = get_session()
    settings_records = db_session.query(SystemSettings).filter(SystemSettings.key.like("sso_state_%")).all()

    sessions_pool = {}
    for rec in settings_records:
        username = rec.key.replace("sso_state_", "")
        cookies = parse_cookies(rec.value)
        if cookies and "SESSION" in cookies:
            sessions_pool[username] = cookies
            print(f"   ✓ Loaded active session for admin: {username} ({len(cookies)} cookies)")

    # Fallback to general sso_cookies if no specific sso_state_% is found
    if not sessions_pool:
        print("   ⚠️ No specific sso_state_% found. Trying fallback to 'sso_cookies'...")
        fallback_rec = db_session.query(SystemSettings).filter_by(key="sso_cookies").first()
        if fallback_rec and fallback_rec.value:
            cookies = parse_cookies(fallback_rec.value)
            if cookies:
                sessions_pool["general_fallback"] = cookies
                print(f"   ✓ Loaded fallback session: general_fallback ({len(cookies)} cookies)")

    if not sessions_pool:
        print("❌ Error: No active sessions found in system_settings table!")
        sys.exit(1)

    print(f"\n   Total active sessions in pool: {len(sessions_pool)}")

    # 2. Retrieve assignments to test
    print("\n[2] Reading 100 random assignments from DB...")
    assignments = db_session.query(Assignment).limit(100).all()
    db_session.close()

    if not assignments:
        print("❌ Error: No assignments found in database to test with.")
        sys.exit(1)

    actual_count = len(assignments)
    print(f"   ✓ Retrieved {actual_count} assignment IDs.")

    # 3. Setup client pool and sessions
    import ssl

    import aiohttp

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # Set total concurrency to 30 (15 concurrent requests per session)
    total_concurrency = len(sessions_pool) * 15
    semaphore = asyncio.Semaphore(total_concurrency)
    print(f"\n[3] Initializing Keep-Alive client sessions with concurrency limit: {total_concurrency}...")

    # We build ClientSession for each user
    connector_opts = {
        "ssl": ssl_ctx,
        "limit": 40,
        "limit_per_host": 25,
        "keepalive_timeout": 120,
        "force_close": False,
    }

    # Queue setup
    queue = asyncio.Queue(maxsize=300)
    db_session_factory = get_session_factory()
    stats = {"success_count": 0}

    t0 = time.perf_counter()

    # Launch multi-session client context
    active_sessions = []
    headers_map = {}

    for username, cookies in sessions_pool.items():
        connector = aiohttp.TCPConnector(**connector_opts)
        session = aiohttp.ClientSession(cookies=cookies, connector=connector)
        active_sessions.append((username, session))

        # Build distinct headers per-session with valid token
        headers_map[username] = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
            "X-XSRF-TOKEN": unquote(cookies.get("XSRF-TOKEN", "")),
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    print(f"\n🚀 Running Multi-Session Pipeline (Total Concurrency: {total_concurrency})...")

    # Start Consumer
    consumer_task = asyncio.create_task(consumer(queue, db_session_factory, stats))

    # Start Producers with round-robin sessions distribution
    producer_tasks = []
    for idx, a in enumerate(assignments):
        # Round-robin session selection
        username, session = active_sessions[idx % len(active_sessions)]
        headers = headers_map[username]

        task = asyncio.create_task(producer(session, str(a.id), a.survey_config_id, queue, semaphore, headers))
        producer_tasks.append(task)

    # Wait for all producers to finish
    producer_results = await asyncio.gather(*producer_tasks)
    successful_fetches = sum(1 for r in producer_results if r)

    # Push sentinel
    await queue.put(None)
    await consumer_task

    # Close all client sessions
    for _, session in active_sessions:
        await session.close()

    duration = time.perf_counter() - t0
    rps = stats["success_count"] / duration if duration > 0 else 0

    print("\n" + "=" * 90)
    print("                      📊  MULTI-SESSION PIPELINE RESULTS  📊                      ")
    print("=" * 90)
    print(f" Active Session Accounts: {', '.join(sessions_pool.keys())}")
    print(f" Target Concurrency Limit: {total_concurrency}")
    print(f" Total Target Records   : {actual_count}")
    print(f" Successfully Fetched   : {successful_fetches}")
    print(f" Successfully Written   : {stats['success_count']}")
    print(f" Total Pipeline Time    : {duration:.3f} seconds")
    print(f" Effective Throughput   : {rps:.2f} records/second")
    print("=" * 90)
    print("🎉 Multi-Session Experiment verification test complete!")


if __name__ == "__main__":
    asyncio.run(main())
