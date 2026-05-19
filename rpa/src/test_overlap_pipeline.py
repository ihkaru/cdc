#!/usr/bin/env python
"""
test_overlap_pipeline.py — Verification benchmark for Overlap Pipeline.
Uses asyncio.Queue as a high-speed buffer between Producers (Fetchers) and Consumer (DB Writer).
Enforces CAPI Mobile Endpoint for ultra-low latency.
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
    print("=" * 85)
    print("       ⚡  FasihNexus — asyncio.Queue Overlap Pipeline Performance Test  ⚡       ")
    print("=" * 85)


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
                            # Put to queue
                            await queue.put(data)
                            return True
        except Exception:
            # Silently log errors
            pass
    return False


async def consumer(queue, db_session_factory, stats):
    """Consumer coroutine: reads from the queue and writes to the DB in batches using BatchUpserterBulk."""
    session = db_session_factory()
    upserter = BatchUpserterBulk(session, batch_size=100)  # batch size 100 for test speed
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

        # Final flush
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

    # 1. Retrieve cookies
    print("[1] Loading SSO cookies from system_settings...")
    db_session = get_session()
    cookie_rec = db_session.query(SystemSettings).filter_by(key="sso_cookies").first()
    if not cookie_rec or not cookie_rec.value:
        print("❌ Error: No valid sso_cookies found in system_settings table!")
        sys.exit(1)

    cookies_dict = json.loads(cookie_rec.value)
    print(f"   ✓ Loaded {len(cookies_dict)} cookies.")

    # 2. Retrieve assignments
    print("\n[2] Reading 100 random assignments from DB...")
    assignments = db_session.query(Assignment).limit(100).all()
    db_session.close()

    if not assignments:
        print("❌ Error: No assignments found in database to test with.")
        sys.exit(1)

    actual_count = len(assignments)
    print(f"   ✓ Retrieved {actual_count} assignment IDs.")

    # Set up HTTP parameters
    import ssl

    import aiohttp

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "X-XSRF-TOKEN": unquote(cookies_dict.get("XSRF-TOKEN", "")),
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    # Queue setup
    queue = asyncio.Queue(maxsize=200)
    semaphore = asyncio.Semaphore(15)  # Concurrency limit of 15
    db_session_factory = get_session_factory()

    stats = {"success_count": 0}

    print("\n🚀 Starting Overlap Pipeline (15 concurrent fetchers ↔ 1 consumer DB writer)...")
    t0 = time.perf_counter()

    # Re-use enterprise-grade TCPConnector
    connector = aiohttp.TCPConnector(
        ssl=ssl_ctx,
        limit=25,
        limit_per_host=15,
        keepalive_timeout=120,
        force_close=False,
    )

    async with aiohttp.ClientSession(cookies=cookies_dict, connector=connector) as session:
        # 1. Start Consumer
        consumer_task = asyncio.create_task(consumer(queue, db_session_factory, stats))

        # 2. Start Producers
        producer_tasks = [
            asyncio.create_task(producer(session, str(a.id), a.survey_config_id, queue, semaphore, headers))
            for a in assignments
        ]

        # Wait for all producers to finish
        producer_results = await asyncio.gather(*producer_tasks)
        successful_fetches = sum(1 for r in producer_results if r)

        # Push sentinel to end consumer
        await queue.put(None)

        # Wait for consumer to finish processing everything in queue
        await consumer_task

    duration = time.perf_counter() - t0
    rps = stats["success_count"] / duration if duration > 0 else 0

    print("\n" + "=" * 85)
    print("                      📊  OVERLAP PIPELINE RESULTS  📊                      ")
    print("=" * 85)
    print(f" Total Target Records   : {actual_count}")
    print(f" Successfully Fetched   : {successful_fetches}")
    print(f" Successfully Written   : {stats['success_count']}")
    print(f" Total Pipeline Time    : {duration:.3f} seconds")
    print(f" Effective Throughput   : {rps:.2f} records/second")
    print("=" * 85)
    print("🎉 Verification Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
