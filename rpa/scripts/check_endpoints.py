import asyncio
import json
import os
import ssl
import sys
import time

import aiohttp

# Add app and src to path inside Docker
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/src")

from api_client import FasihApiClient, FasihAuthError
from db.connection import get_session
from db.models import SurveyConfig, SystemSettings


def print_section(title):
    print("\n" + "=" * 80)
    print(f"  📊  {title}")
    print("=" * 80)


async def test_survey_endpoints(api, survey_name, period_id):
    # Probing payloads
    lengths = [0, 100, 500, 1000]
    paths = [
        "analytic/api/v2/assignment/datatable-all-user-survey-periode",
        "app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode",
    ]

    target_url = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id").rstrip("/")
    headers = api._get_headers()
    headers["Content-Type"] = "application/json"

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # 1. Test Endpoint Routes
    print(f"\n--- [1] ROUTE TESTING FOR: {survey_name} ---")
    for path in paths:
        url = f"{target_url}/{path}"
        payload = {
            "draw": 1,
            "columns": [
                {"data": "id", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}}
            ],
            "order": [{"column": 0, "dir": "asc"}],
            "start": 0,
            "length": 1,  # minimal length for routing test
            "search": {"value": "", "regex": False},
            "assignmentExtraParam": {
                "surveyPeriodId": period_id,
                "assignmentErrorStatusType": -1,
                "filterTargetType": "ALL",
            },
        }

        t0 = time.perf_counter()
        try:
            async with aiohttp.ClientSession(
                cookies=api.cookies, connector=aiohttp.TCPConnector(ssl=ssl_ctx)
            ) as session:
                async with session.post(
                    url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    duration = time.perf_counter() - t0
                    status = resp.status
                    if status == 200:
                        print(f"   🟢 SUCCESS | Route: /{path} | Status: 200 | Latency: {duration:.3f}s")
                    else:
                        print(f"   🔴 FAILURE | Route: /{path} | Status: {status} | Latency: {duration:.3f}s")
        except Exception as e:
            duration = time.perf_counter() - t0
            print(f"   🔴 TIMEOUT/ERROR | Route: /{path} | Error: {e} | Latency: {duration:.3f}s")

    # 2. Test Scalability / Timeout Thresholds
    print("\n--- [2] SCALABILITY & TIMEOUT DIAGNOSTIC (page size vs query latency) ---")
    print(f"    Target Endpoint: {target_url}/{paths[0]}")

    for length in lengths:
        payload = {
            "draw": 1,
            "columns": [
                {"data": "id", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
                {
                    "data": "codeIdentity",
                    "searchable": True,
                    "orderable": False,
                    "search": {"value": "", "regex": False},
                },
            ],
            "order": [{"column": 0, "dir": "asc"}],
            "start": 0,
            "length": length,
            "search": {"value": "", "regex": False},
            "assignmentExtraParam": {
                "surveyPeriodId": period_id,
                "assignmentErrorStatusType": -1,
                "filterTargetType": "ALL",
            },
        }

        t0 = time.perf_counter()
        try:
            async with aiohttp.ClientSession(
                cookies=api.cookies, connector=aiohttp.TCPConnector(ssl=ssl_ctx)
            ) as session:
                async with session.post(
                    f"{target_url}/{paths[0]}", headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=40)
                ) as resp:
                    duration = time.perf_counter() - t0
                    status = resp.status

                    if status == 200:
                        text = await resp.text()
                        data = json.loads(text)
                        records_total = data.get("recordsTotal") or data.get("totalHit") or 0
                        search_data_len = len(data.get("searchData", [])) or len(data.get("data", []))
                        print(
                            f"   🟢 Page Size: {length:<4} | Status: 200 | Latency: {duration:>6.3f}s | Returned: {search_data_len:<4} | Total: {records_total}"
                        )
                    else:
                        print(f"   🔴 Page Size: {length:<4} | Status: {status} | Latency: {duration:>6.3f}s | FAILED")
        except asyncio.TimeoutError:
            duration = time.perf_counter() - t0
            print(
                f"   ⚠️  Page Size: {length:<4} | Status: 504 (TIMEOUT) | Latency: {duration:>6.3f}s | FAILED (Gateway timeout threshold exceeded!)"
            )
        except Exception as e:
            duration = time.perf_counter() - t0
            print(f"   🔴 Page Size: {length:<4} | Status: ERROR | Latency: {duration:>6.3f}s | Detail: {e}")

        # Jitter pause
        await asyncio.sleep(1)


async def run_diagnostics():
    print_section("FasihNexus — BPS API Endpoint Diagnostic Tool")

    # 1. Check database session
    db_url = os.getenv("DATABASE_URL")
    print(f"🔌 Connecting to database: {db_url.split('@')[1] if db_url and '@' in db_url else 'Default'}")

    session = get_session()

    # 2. Retrieve active configs
    active_configs = session.query(SurveyConfig).filter(SurveyConfig.is_active == True).all()
    print(f"📊 Found {len(active_configs)} active survey configuration(s) in database.")

    for survey in active_configs:
        print("\n────────────────────────────────────────────────────────────────────────")
        print(f" SURVEY: {survey.survey_name} (User: {survey.sso_username})")
        print("────────────────────────────────────────────────────────────────────────")

        # Load user cookies from DB (trying multiple keys to handle user mappings)
        cache_keys = [
            f"sso_cookies_{survey.sso_username.split('@')[0]}_test",
            f"sso_cookies_{survey.sso_username}",
            f"sso_cookies_{survey.sso_username.split('@')[0]}",
            "sso_cookies",
        ]
        cookie_rec = None
        for key in cache_keys:
            cookie_rec = session.query(SystemSettings).filter_by(key=key).first()
            if cookie_rec and cookie_rec.value:
                print(f"✓ Loaded session cookies from key: '{key}'")
                break

        if not cookie_rec or not cookie_rec.value:
            print("❌ Error: No session cookies stored in database for this user!")
            continue

        cookies = json.loads(cookie_rec.value)
        print(f"✓ Loaded {len(cookies)} session cookies.")

        # Resolve survey period and test endpoints
        try:
            async with FasihApiClient(cookies) as api:
                print("🔍 Probing metadata keys on BPS API...")
                survey_id = await api.get_survey_id(survey.survey_name)
                if not survey_id:
                    print("❌ Failure: Survey not found/access denied.")
                    continue

                period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)
                if not period_id:
                    print("❌ Failure: Survey period ID not found.")
                    continue

                print(f"✓ Survey ID: {survey_id}")
                print(f"✓ Period ID: {period_id}")

                await test_survey_endpoints(api, survey.survey_name, period_id)

        except FasihAuthError:
            print("❌ Session Expired: Keycloak redirect triggered. Credentials need re-authentication.")
        except Exception as e:
            print(f"❌ Error during API diagnostic run: {e}")
            import traceback

            traceback.print_exc()

    session.close()
    print_section("Diagnostic Run Completed")


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
