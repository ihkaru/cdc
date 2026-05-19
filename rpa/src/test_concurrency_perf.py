#!/usr/bin/env python
"""
test_concurrency_perf.py — Concurrency Stress Test for FasihNexus RPA detail fetches.
Runs fetches using varying concurrency levels to determine the optimal speed/safety trade-off.
"""

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import get_session
from db.models import Assignment, SystemSettings
from pages.detail_page import fetch_assignments_concurrent


def print_banner():
    print("=" * 75)
    print("        📊  FasihNexus — Concurrency Performance Experiment Runner  📊        ")
    print("=" * 75)


async def test_probe(cookies_dict) -> bool:
    """Fast probe to see if BPS connection is alive and session is active."""
    import ssl
    from urllib.parse import unquote

    import aiohttp

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # Replicate precise browser headers
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Extract and decode XSRF token
    xsrf = cookies_dict.get("XSRF-TOKEN")
    if xsrf:
        headers["X-XSRF-TOKEN"] = unquote(xsrf)

    url = "https://fasih-sm.bps.go.id/survey/api/v1/surveys/datatable?surveyType=Pencacahan"
    payload = {"pageNumber": 0, "pageSize": 1, "sortBy": "CREATED_AT", "sortDirection": "DESC", "keywordSearch": ""}
    try:
        async with aiohttp.ClientSession(cookies=cookies_dict, connector=aiohttp.TCPConnector(ssl=ssl_ctx)) as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("success", False)
                else:
                    body = await resp.text()
                    print(f"   ⚠️  Probe returned status {resp.status}. Response: {body[:200]}")
    except Exception as e:
        print(f"   ⚠️  Probe check failed with exception: {e}")
    return False


async def main():
    parser = argparse.ArgumentParser(description="Run concurrency performance test.")
    parser.add_argument(
        "-c",
        "--concurrency-list",
        type=str,
        default="5,10,20,30,40,50",
        help="Comma-separated list of concurrency limits to test",
    )
    parser.add_argument("-l", "--limit", type=int, default=30, help="Number of records to fetch per concurrency run")
    parser.add_argument(
        "-o", "--output", type=str, default="concurrency_results.json", help="Path to save output results JSON"
    )
    args = parser.parse_args()

    print_banner()

    # 1. Retrieve cookies
    print("[1] Loading SSO cookies from system_settings...")
    session = get_session()
    cookie_rec = session.query(SystemSettings).filter_by(key="sso_cookies").first()
    if not cookie_rec or not cookie_rec.value:
        print("❌ Error: No valid sso_cookies found in system_settings table! Please run a sync once first.")
        sys.exit(1)

    cookies_dict = json.loads(cookie_rec.value)
    print("   ✓ Loaded cookies successfully.")

    # 2. Check VPN/Session status
    print("\n[2] Probing BPS Fasih-SM connection...")
    alive = await test_probe(cookies_dict)
    if not alive:
        print("   ⚠️  Warning: SSO session probe failed. The session might be expired or WAF blocked the probe.")
        print("      Continuing anyway to run the concurrency benchmark...")
    else:
        print("   ✓ Session is ACTIVE and reachable.")

    # 3. Retrieve assignment IDs
    print(f"\n[3] Reading {args.limit} random assignments from DB...")
    assignments = session.query(Assignment).limit(args.limit).all()
    session.close()

    if not assignments:
        print("❌ Error: No assignments found in database. Cannot run fetch test!")
        sys.exit(1)

    actual_count = len(assignments)
    print(f"   ✓ Retrieved {actual_count} assignment IDs.")

    # Generate dummy URLs that pages/detail_page.py can extract IDs from
    urls = [f"https://fasih-sm.bps.go.id/survey-collection/assignment-detail/{a.id}/dummy" for a in assignments]

    concurrencies = [int(x.strip()) for x in args.concurrency_list.split(",")]

    results = []

    print("\n[4] Starting Concurrency Stress Test Loop...")
    print("=" * 75)

    for c in concurrencies:
        print(f"\n🚀 Running experiment with Concurrency = {c} (Fetching {actual_count} items)...")

        t0 = time.perf_counter()

        # We capture on_progress to compute successes and failures
        success_count = 0
        fail_count = 0

        async def on_progress(completed, total, data):
            nonlocal success_count, fail_count
            if data:
                success_count += 1
            else:
                fail_count += 1

        # Run the concurrent fetch
        await fetch_assignments_concurrent(cookie_dict=cookies_dict, urls=urls, concurrency=c, on_progress=on_progress)

        duration = time.perf_counter() - t0
        success_rate = (success_count / actual_count) * 100 if actual_count > 0 else 0
        rps = success_count / duration if duration > 0 else 0

        print(f"   ⏱️ Finished: {success_count}/{actual_count} successful in {duration:.2f} seconds.")
        print(f"   ⚡ Concurrency: {c} | Success Rate: {success_rate:.1f}% | Thruput: {rps:.2f} rps")

        results.append(
            {
                "concurrency": c,
                "total_items": actual_count,
                "success_count": success_count,
                "fail_count": fail_count,
                "duration_sec": duration,
                "success_rate": success_rate,
                "requests_per_sec": rps,
            }
        )

        # Soft sleep to allow BPS F5 gateway/rate-limits to reset
        print("   💤 Cooling down for 3 seconds...")
        await asyncio.sleep(3)

    # Print gorgeous report table
    print("\n" + "=" * 75)
    print("                      📊  FINAL COMPARATIVE REPORT  📊                      ")
    print("=" * 75)
    print(
        f" {'Concurrency':<12} | {'Success Count':<15} | {'Duration (s)':<12} | {'Success %':<10} | {'Throughput':<12}"
    )
    print("-" * 75)
    for r in results:
        duration_str = f"{r['duration_sec']:.2f}"
        success_pct_str = f"{r['success_rate']:.1f}%"
        rps_str = f"{r['requests_per_sec']:.2f} r/s"
        print(
            f" {r['concurrency']:<12} | {r['success_count']:<15} | {duration_str:<12} | {success_pct_str:<10} | {rps_str:<12}"
        )
    print("=" * 75)

    # Save to file
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"📁 Raw results successfully saved to: {args.output}\n")


if __name__ == "__main__":
    asyncio.run(main())
