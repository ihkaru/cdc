import os
import asyncio
import time
import json
import ssl
import aiohttp
from fastapi import APIRouter, HTTPException
from typing import Optional

from schemas import LookupRequest, KabupatenLookupRequest, ProbeRequest
from auth import auto_login, launch_stealth_browser, new_stealth_context
from connectivity import ensure_connected
from db.connection import get_session

router = APIRouter()

@router.post("/lookup/metadata")
async def lookup_metadata(req: LookupRequest):
    """Metadata lookup using Storage State + Force XSRF Maturation."""
    start_total = time.perf_counter()
    timings = {}
    
    # PHASE 1: VPN
    await ensure_connected()
    timings["vpn_ensure_ms"] = int((time.perf_counter() - start_total) * 1000)

    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
    CACHE_KEY  = f"sso_state_{req.sso_username}"

    # PHASE 2: Storage State Cache
    t_cache = time.perf_counter()
    with get_session() as db:
        from db.models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.key == CACHE_KEY).first()
        storage_state_json = setting.value if setting else None
        
        if storage_state_json:
            try:
                storage_state = json.loads(storage_state_json)
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await launch_stealth_browser(p)
                    context = await new_stealth_context(browser, storage_state=storage_state)
                    page = await context.new_page()
                    
                    # Verify session with a quick API hit
                    # Also serves to populate cookies in browser context
                    try:
                        api_resp = await page.request.get(f"{TARGET_URL}/region/api/v1/region/level1?groupId=82af087a-d063-48b9-8633-71c84c4e7422", timeout=10000)
                        if api_resp.status == 200 and "oauth_login" not in api_resp.url:
                            print("   ⚡ [Lookup] Storage state VALID. Fetching via browser request...")
                            
                            cookies = await context.cookies()
                            xsrf = next((c['value'] for c in cookies if c['name'] == 'XSRF-TOKEN'), None)
                            print(f"   ⚡ [Lookup] XSRF-TOKEN present in cookies: {bool(xsrf)}")
                            
                            from urllib.parse import unquote
                            headers = {
                                "X-XSRF-TOKEN": unquote(xsrf) if xsrf else "",
                                "X-Requested-With": "XMLHttpRequest",
                                "Content-Type": "application/json",
                            }
                            
                            surveys_resp = await page.request.post(
                                f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                                data=json.dumps({"pageNumber": 0, "pageSize": 100, "sortBy": "CREATED_AT", "sortDirection": "DESC", "keywordSearch": ""}),
                                headers=headers,
                                timeout=15000
                            )
                            
                            if surveys_resp.status == 200:
                                surveys_data = await surveys_resp.json()
                                items = surveys_data.get("data", {}).get("content", [])
                                surveys = [{"id": s.get("id"), "name": s.get("name") or s.get("surveyName", "")} for s in items]
                                
                                prov_data = await api_resp.json()
                                provinces = [{"id": r.get("id"), "name": r.get("name", ""), "fullCode": r.get("fullCode", "")} for r in prov_data.get("data", [])]
                                
                                await browser.close()
                                timings["cache_hit"] = True
                                timings["total_ms"] = int((time.perf_counter() - start_total) * 1000)
                                print(f"   ✨ [Lookup] FAST CACHE SUCCESS in {timings['total_ms']}ms")
                                return {"surveys": surveys, "provinces": provinces, "debug_timings": timings}
                            else:
                                print(f"   ⚠️ [Lookup] Cache check failed at survey fetch. Status: {surveys_resp.status}")
                                print(f"   ⚠️ [Lookup] Survey fetch response: {await surveys_resp.text()}")
                        else:
                            print(f"   ⚠️ [Lookup] Cache check failed at API resp. Status: {api_resp.status}, URL: {api_resp.url}")
                    except Exception as e:
                        print(f"   ⚠️ [Lookup] Cache validation error: {e}")
                    
                    await browser.close()
            except Exception as e:
                print(f"   ❌ [Lookup] Cache phase error: {e}")

    timings["cache_hit"] = False
    timings["cache_check_ms"] = int((time.perf_counter() - t_cache) * 1000)

    # PHASE 3: Full Login
    t_browser = time.perf_counter()
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await launch_stealth_browser(p)
        context = await new_stealth_context(browser)
        try:
            page = await context.new_page()
            success, _, err_msg = await auto_login(page, req.sso_username, req.sso_password)
            if not success:
                raise HTTPException(status_code=401, detail=f"Login gagal: {err_msg}")
            
            # --- FORCE XSRF MATURATION ---
            print("   🎣 [Lookup] Forcing XSRF maturation via API hit...")
            await page.goto(f"{TARGET_URL}/region/api/v1/region/level1?groupId=82af087a-d063-48b9-8633-71c84c4e7422", wait_until="networkidle", timeout=15000)
            
            # Save state (now with XSRF-TOKEN hopefully)
            state = await context.storage_state()
            with get_session() as db:
                from db.repository import set_system_setting
                set_system_setting(db, CACHE_KEY, json.dumps(state))

            # Initial Fetch
            cookies = await context.cookies()
            xsrf = next((c['value'] for c in cookies if c['name'] == 'XSRF-TOKEN'), None)
            from urllib.parse import unquote
            headers = {
                "X-XSRF-TOKEN": unquote(xsrf) if xsrf else "",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",
            }
            
            surveys_resp = await page.request.post(
                f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                data=json.dumps({"pageNumber": 0, "pageSize": 100, "sortBy": "CREATED_AT", "sortDirection": "DESC", "keywordSearch": ""}),
                headers=headers,
                timeout=15000
            )
            surveys_data = await surveys_resp.json()
            items = surveys_data.get("data", {}).get("content", [])
            surveys = [{"id": s.get("id"), "name": s.get("name") or s.get("surveyName", "")} for s in items]
            
            prov_resp = await page.request.get(f"{TARGET_URL}/region/api/v1/region/level1?groupId=82af087a-d063-48b9-8633-71c84c4e7422", timeout=15000)
            prov_data = await prov_resp.json()
            provinces = [{"id": r.get("id"), "name": r.get("name", ""), "fullCode": r.get("fullCode", "")} for r in prov_data.get("data", [])]

            timings["sso_login_ms"] = int((time.perf_counter() - t_browser) * 1000)
            timings["total_ms"] = int((time.perf_counter() - start_total) * 1000)
            return {"surveys": surveys, "provinces": provinces, "debug_timings": timings}
        finally:
            await browser.close()

@router.post("/lookup/kabupaten")
async def lookup_kabupaten(req: KabupatenLookupRequest):
    """Fast kabupaten lookup using Storage State."""
    await ensure_connected()
    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
    CACHE_KEY  = f"sso_state_{req.sso_username}"
    with get_session() as db:
        from db.models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.key == CACHE_KEY).first()
        state_json = setting.value if setting else None
        if state_json:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await launch_stealth_browser(p)
                    context = await new_stealth_context(browser, storage_state=json.loads(state_json))
                    page = await context.new_page()
                    # Hit API directly
                    resp = await page.request.get(f"{TARGET_URL}/region/api/v1/region/level2?level1FullCode={req.prov_full_code}", timeout=10000)
                    if resp.status == 200:
                        data = await resp.json()
                        kab = [{"id": r.get("id"), "name": r.get("name", ""), "fullCode": r.get("fullCode", "")} for r in data.get("data", [])]
                        await browser.close()
                        return {"kabupaten": kab}
                    await browser.close()
            except: pass
    raise HTTPException(status_code=401, detail="Session expired")
