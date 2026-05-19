#!/usr/bin/env python
"""
test_concurrency_perf_v2.py — Advanced Concurrency & Engine Comparison Benchmark.
Compares aiohttp (Default) vs aiohttp + orjson vs curl_cffi (Chrome Impersonated) + orjson.
"""

import argparse
import asyncio
import os
import sys
import time
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import get_session
from db.models import Assignment, SystemSettings

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
API_BASE = f"{TARGET_URL}/assignment-general/api/assignment/get-by-id-with-data-for-scm"


def print_banner():
    print("=" * 85)
    print("      📊  FasihNexus — Advanced Concurrency Engine Comparison Benchmark  📊      ")
    print("=" * 85)


async def run_aiohttp_default(cookies_dict, urls, concurrency):
    import ssl

    import aiohttp

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "X-XSRF-TOKEN": unquote(cookies_dict.get("XSRF-TOKEN", "")),
    }

    semaphore = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def fetch_one(session, url):
        nonlocal success, fail
        async with semaphore:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        body = await resp.json()  # Uses standard json.loads
                        if body and body.get("success"):
                            success += 1
                            return
                    fail += 1
            except Exception:
                fail += 1

    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit_per_host=concurrency, keepalive_timeout=60)
    async with aiohttp.ClientSession(cookies=cookies_dict, connector=connector) as session:
        tasks = [asyncio.create_task(fetch_one(session, u)) for u in urls]
        await asyncio.gather(*tasks, return_exceptions=True)

    return success, fail


async def run_aiohttp_orjson(cookies_dict, urls, concurrency):
    import ssl

    import aiohttp
    import orjson

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "X-XSRF-TOKEN": unquote(cookies_dict.get("XSRF-TOKEN", "")),
    }

    semaphore = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def fetch_one(session, url):
        nonlocal success, fail
        async with semaphore:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        # Optimization: Using orjson for extremely fast loads
                        body = await resp.json(loads=orjson.loads)
                        if body and body.get("success"):
                            success += 1
                            return
                    fail += 1
            except Exception:
                fail += 1

    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit_per_host=concurrency, keepalive_timeout=60)
    async with aiohttp.ClientSession(cookies=cookies_dict, connector=connector) as session:
        tasks = [asyncio.create_task(fetch_one(session, u)) for u in urls]
        await asyncio.gather(*tasks, return_exceptions=True)

    return success, fail


async def run_curl_cffi_orjson(cookies_dict, urls, concurrency):
    import orjson
    from curl_cffi.requests import AsyncSession

    headers = {
        "Accept": "application/json, text/plain, */*",
        "X-XSRF-TOKEN": unquote(cookies_dict.get("XSRF-TOKEN", "")),
    }

    semaphore = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def fetch_one(session, url):
        nonlocal success, fail
        async with semaphore:
            try:
                # Disabling SSL validation (verify=False) since we are inside BPS VPN
                resp = await session.get(url, headers=headers, timeout=20, verify=False)
                if resp.status_code == 200:
                    body = orjson.loads(resp.content)
                    if body and body.get("success"):
                        success += 1
                        return
                fail += 1
            except Exception:
                fail += 1

    # Impersonate Chrome 120 directly at the TLS/JA3 level!
    async with AsyncSession(cookies=cookies_dict, impersonate="chrome120", max_clients=concurrency) as session:
        tasks = [asyncio.create_task(fetch_one(session, u)) for u in urls]
        await asyncio.gather(*tasks, return_exceptions=True)

    return success, fail


async def main():
    parser = argparse.ArgumentParser(description="Run comparison concurrency benchmark.")
    parser.add_argument("-c", "--concurrency", type=int, default=15, help="Concurrency limit to use")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Number of records to fetch")
    args = parser.parse_args()

    print_banner()

    # 1. Retrieve cookies
    print("[1] Loading SSO cookies from system_settings...")
    session = get_session()
    cookie_rec = session.query(SystemSettings).filter_by(key="sso_cookies").first()
    if not cookie_rec or not cookie_rec.value:
        print("❌ Error: No valid sso_cookies found in system_settings table!")
        sys.exit(1)

    import json

    cookies_dict = json.loads(cookie_rec.value)
    print("   ✓ Loaded cookies successfully.")

    # 2. Retrieve assignment IDs
    print(f"\n[2] Reading {args.limit} random assignments from DB...")
    assignments = session.query(Assignment).limit(args.limit).all()
    session.close()

    if not assignments:
        print("❌ Error: No assignments found in database.")
        sys.exit(1)

    actual_count = len(assignments)
    print(f"   ✓ Retrieved {actual_count} assignment IDs.")
    urls = [f"{API_BASE}?id={a.id}" for a in assignments]

    results = {}

    # Experiment 1: aiohttp (Default)
    print(f"\n🚀 Running Experiment 1: aiohttp (Default, json) | Concurrency = {args.concurrency}...")
    t0 = time.perf_counter()
    success, fail = await run_aiohttp_default(cookies_dict, urls, args.concurrency)
    duration_1 = time.perf_counter() - t0
    rps_1 = success / duration_1 if duration_1 > 0 else 0
    print(f"   ⏱️ Result: {success}/{actual_count} OK in {duration_1:.2f}s | Throughput: {rps_1:.2f} req/s")
    results["aiohttp_default"] = {"success": success, "duration": duration_1, "rps": rps_1}

    print("   💤 Cooling down for 3 seconds...")
    await asyncio.sleep(3)

    # Experiment 2: aiohttp + orjson
    print(f"\n🚀 Running Experiment 2: aiohttp + orjson | Concurrency = {args.concurrency}...")
    t0 = time.perf_counter()
    success, fail = await run_aiohttp_orjson(cookies_dict, urls, args.concurrency)
    duration_2 = time.perf_counter() - t0
    rps_2 = success / duration_2 if duration_2 > 0 else 0
    print(f"   ⏱️ Result: {success}/{actual_count} OK in {duration_2:.2f}s | Throughput: {rps_2:.2f} req/s")
    results["aiohttp_orjson"] = {"success": success, "duration": duration_2, "rps": rps_2}

    print("   💤 Cooling down for 3 seconds...")
    await asyncio.sleep(3)

    # Experiment 3: curl_cffi + orjson
    print(f"\n🚀 Running Experiment 3: curl_cffi (Impersonated) + orjson | Concurrency = {args.concurrency}...")
    t0 = time.perf_counter()
    success, fail = await run_curl_cffi_orjson(cookies_dict, urls, args.concurrency)
    duration_3 = time.perf_counter() - t0
    rps_3 = success / duration_3 if duration_3 > 0 else 0
    print(f"   ⏱️ Result: {success}/{actual_count} OK in {duration_3:.2f}s | Throughput: {rps_3:.2f} req/s")
    results["curl_cffi_orjson"] = {"success": success, "duration": duration_3, "rps": rps_3}

    # Print Report
    print("\n" + "=" * 85)
    print("                         📊  BENCHMARK ENGINE REPORT  📊                         ")
    print("=" * 85)
    print(f" {'HTTP Client Engine':<32} | {'Success Count':<15} | {'Duration (s)':<12} | {'Throughput':<12}")
    print("-" * 85)
    for name, data in results.items():
        print(f" {name:<32} | {data['success']:<15} | {data['duration']:<12.2f} | {data['rps']:<12.2f} r/s")
    print("=" * 85)
    print("🎉 Benchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
