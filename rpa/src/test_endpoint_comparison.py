#!/usr/bin/env python
"""
test_endpoint_comparison.py — Comparison benchmark between:
1. Web SCM Endpoint: /assignment-general/api/assignment/get-by-id-with-data-for-scm?id={id}
2. Mobile CAPI Endpoint: /app/api/assignment-general/api/assignment/get-by-assignment-id?assignmentId={id}
"""

import asyncio
import json
import os
import sys
import time
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import get_session
from db.models import Assignment, SystemSettings

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")


def print_banner():
    print("=" * 85)
    print("        📊  FasihNexus — Web SCM vs CAPI Mobile Endpoint Comparison  📊        ")
    print("=" * 85)


async def main():
    print_banner()

    # 1. Retrieve cookies
    print("[1] Loading SSO cookies from system_settings...")
    session = get_session()
    cookie_rec = session.query(SystemSettings).filter_by(key="sso_cookies").first()
    if not cookie_rec or not cookie_rec.value:
        print("❌ Error: No valid sso_cookies found in system_settings table!")
        sys.exit(1)

    cookies_dict = json.loads(cookie_rec.value)
    print(f"   ✓ Loaded {len(cookies_dict)} cookies.")

    # 2. Retrieve assignments
    print("\n[2] Reading 5 sample assignments from DB...")
    assignments = session.query(Assignment).limit(5).all()
    session.close()

    if not assignments:
        print("❌ Error: No assignments found in database to test with.")
        sys.exit(1)

    print(f"   ✓ Retrieved {len(assignments)} sample assignments.")

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
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    results = []

    # Configure session
    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=1)
    async with aiohttp.ClientSession(cookies=cookies_dict, connector=connector) as http_session:
        for idx, a in enumerate(assignments, 1):
            aid = str(a.id)
            print(f"\n--- Testing Assignment {idx} ({aid}) ---")

            # A. Web SCM
            url_web = f"{TARGET_URL}/assignment-general/api/assignment/get-by-id-with-data-for-scm?id={aid}"
            t0 = time.perf_counter()
            size_web = 0
            success_web = False
            error_web = ""
            try:
                async with http_session.get(url_web, headers=headers, timeout=20) as resp:
                    duration_web = time.perf_counter() - t0
                    status_web = resp.status
                    if status_web == 200:
                        body_bytes = await resp.read()
                        size_web = len(body_bytes)
                        body = orjson.loads(body_bytes)
                        if body.get("success"):
                            success_web = True
                        else:
                            error_web = f"API Error: {body.get('message', 'unknown')}"
                    else:
                        error_web = f"HTTP {status_web}"
            except Exception as e:
                duration_web = time.perf_counter() - t0
                error_web = str(e)

            print(
                f"   🌐 [Web SCM] Status: {'✅ OK' if success_web else '❌ FAIL (' + error_web + ')'} | Latency: {duration_web:.3f}s | Size: {size_web / 1024:.2f} KB"
            )

            # B. Mobile CAPI
            # Some environments might have the app URL mapped to /app/api or /api
            # Let's clean the TARGET_URL and verify
            url_capi = f"{TARGET_URL}/app/api/assignment-general/api/assignment/get-by-assignment-id?assignmentId={aid}"
            t0 = time.perf_counter()
            size_capi = 0
            success_capi = False
            error_capi = ""
            try:
                async with http_session.get(url_capi, headers=headers, timeout=20) as resp:
                    duration_capi = time.perf_counter() - t0
                    status_capi = resp.status
                    if status_capi == 200:
                        body_bytes = await resp.read()
                        size_capi = len(body_bytes)
                        body = orjson.loads(body_bytes)
                        if body.get("success"):
                            success_capi = True
                        else:
                            error_capi = f"API Error: {body.get('message', 'unknown')}"
                    else:
                        error_capi = f"HTTP {status_capi}"
            except Exception as e:
                duration_capi = time.perf_counter() - t0
                error_capi = str(e)

            print(
                f"   📱 [CAPI Mobile] Status: {'✅ OK' if success_capi else '❌ FAIL (' + error_capi + ')'} | Latency: {duration_capi:.3f}s | Size: {size_capi / 1024:.2f} KB"
            )

            results.append(
                {
                    "id": aid,
                    "web": {"success": success_web, "latency": duration_web, "size": size_web, "err": error_web},
                    "capi": {"success": success_capi, "latency": duration_capi, "size": size_capi, "err": error_capi},
                }
            )

    # Summary table
    print("\n" + "=" * 85)
    print("                        📊  ENDPOINT COMPARISON SUMMARY  📊                        ")
    print("=" * 85)
    print(
        f" {'ID (Sample)':<8} | {'Web Latency (s)':<17} | {'CAPI Latency (s)':<18} | {'Web Size':<10} | {'CAPI Size':<10}"
    )
    print("-" * 85)
    for r in results:
        w_lat = f"{r['web']['latency']:.3f}s" if r["web"]["success"] else "FAIL"
        c_lat = f"{r['capi']['latency']:.3f}s" if r["capi"]["success"] else "FAIL"
        w_size = f"{r['web']['size'] / 1024:.1f} KB" if r["web"]["success"] else "-"
        c_size = f"{r['capi']['size'] / 1024:.1f} KB" if r["capi"]["success"] else "-"
        print(f" {r['id'][:8]} | {w_lat:<17} | {c_lat:<18} | {w_size:<10} | {c_size:<10}")
    print("=" * 85)


if __name__ == "__main__":
    asyncio.run(main())
