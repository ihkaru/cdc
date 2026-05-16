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

from datetime import datetime, timezone, timedelta

router = APIRouter()

@router.post("/lookup/metadata")
async def lookup_metadata(req: LookupRequest):
    """Metadata lookup using Storage State + Force XSRF Maturation."""
    start_total = time.perf_counter()
    timings = {}

    # PHASE 0: User-Specific Metadata Cache (ULTRA FAST)
    from db.models import SystemSettings
    from datetime import timedelta
    CACHE_KEY_GLOBAL = f"metadata_cache_{req.sso_username}"
    
    with get_session() as db:
        cache = db.query(SystemSettings).filter(SystemSettings.key == CACHE_KEY_GLOBAL).first()
        if cache and cache.updated_at:
            # Check if cache is fresh (e.g., < 6 hours)
            age = datetime.now(timezone.utc) - cache.updated_at.replace(tzinfo=timezone.utc)
            if age < timedelta(hours=6):
                print(f"   ✨ [Lookup] Serving from USER CACHE for {req.sso_username} (Age: {age.total_seconds()/60:.1f}m)")
                data = json.loads(cache.value)
                data["debug_timings"] = {"cache_hit": "USER_CACHE", "total_ms": 0}
                return data

    # PHASE 1: VPN
    await ensure_connected()
    timings["vpn_ensure_ms"] = int((time.perf_counter() - start_total) * 1000)

    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
    CACHE_KEY  = f"sso_state_{req.sso_username}"

    # PHASE 2: Storage State Cache (Fast HTTP Check)
    t_cache = time.perf_counter()
    with get_session() as db:
        from db.models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.key == CACHE_KEY).first()
        storage_state_json = setting.value if setting else None
        
        if storage_state_json:
            try:
                state = json.loads(storage_state_json)
                # Convert Playwright storage state to aiohttp cookies
                cookies = {c['name']: c['value'] for c in state.get('cookies', [])}
                xsrf = next((c['value'] for c in state.get('cookies', []) if c['name'] == 'XSRF-TOKEN'), None)
                
                # Check session validity via tiny API hit (no browser)
                async with aiohttp.ClientSession(cookies=cookies) as session:
                    from urllib.parse import unquote
                    headers = {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-XSRF-TOKEN": unquote(xsrf) if xsrf else "",
                    }
                    
                    # Verify session with region API
                    async with session.get(f"{TARGET_URL}/region/api/v1/region/level1?groupId=82af087a-d063-48b9-8633-71c84c4e7422", headers=headers, timeout=10) as api_resp:
                        if api_resp.status == 200:
                            # Session OK! Now fetch surveys
                            async with session.post(
                                f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                                json={"pageNumber": 0, "pageSize": 100, "sortBy": "CREATED_AT", "sortDirection": "DESC", "keywordSearch": ""},
                                headers=headers,
                                timeout=15
                            ) as surveys_resp:
                                if surveys_resp.status == 200:
                                    print("   ⚡ [Lookup] FAST HTTP CACHE SUCCESS.")
                                    surveys_data = await surveys_resp.json()
                                    prov_data = await api_resp.json()
                                    
                                    items = surveys_data.get("data", {}).get("content", [])
                                    surveys = [{"id": s.get("id"), "name": s.get("name") or s.get("surveyName", "")} for s in items]
                                    
                                    # Clean provinces: filter empty, handle duplicates with same fullCode
                                    raw_provinces = prov_data.get("data", [])
                                    provinces_map = {}
                                    for r in raw_provinces:
                                        fcode = r.get("fullCode")
                                        name = r.get("name", "").strip()
                                        if not fcode or not name: continue
                                        # Prefer name without brackets if both exist
                                        if fcode not in provinces_map or "[" not in name:
                                            provinces_map[fcode] = {"id": r.get("id"), "name": name, "fullCode": fcode}
                                    
                                    provinces = sorted(list(provinces_map.values()), key=lambda x: x["fullCode"])
                                    
                                    timings["cache_hit"] = True
                                    timings["total_ms"] = int((time.perf_counter() - start_total) * 1000)
                                    result = {"surveys": surveys, "provinces": provinces}
                                    try:
                                        with get_session() as db_write:
                                            from db.repository import set_system_setting
                                            set_system_setting(db_write, CACHE_KEY_GLOBAL, json.dumps(result))
                                            print(f"   ✅ [Lookup] USER CACHE UPDATED for {req.sso_username} (Fast Path).")
                                    except Exception as cache_err:
                                        print(f"   ⚠️ [Lookup] Failed to update user cache: {cache_err}")
                                    
                                    result["debug_timings"] = timings
                                    return result
                        
                        print(f"   ⚠️ [Lookup] Cache check failed (HTTP {api_resp.status}). Falling back to browser...")
            except Exception as e:
                print(f"   ❌ [Lookup] Fast Cache check error: {e}")

    timings["cache_hit"] = False
    timings["cache_check_ms"] = int((time.perf_counter() - t_cache) * 1000)

    # PHASE 3: Full Login (Browser Fallback)
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
            print("   🎣 [Lookup] Forcing XSRF maturation...")
            await page.goto(f"{TARGET_URL}/survey/list.html", wait_until="networkidle", timeout=20000)
            
            # Wait for XSRF cookie to appear
            for _ in range(5):
                cookies = await context.cookies()
                if any(c['name'] == 'XSRF-TOKEN' for c in cookies): break
                await asyncio.sleep(1)

            # Save state
            state = await context.storage_state()
            with get_session() as db:
                from db.repository import set_system_setting
                set_system_setting(db, CACHE_KEY, json.dumps(state))
                
                # --- NEW: Sync SVPNCOOKIE to VPN Container ---
                vpn_cookie = next((c['value'] for c in cookies if c['name'] == 'SVPNCOOKIE'), None)
                if vpn_cookie:
                    from auth import sync_cookie_to_db
                    await sync_cookie_to_db(vpn_cookie)
                    print(f"   🛡️ [Lookup] SVPNCOOKIE synchronized to DB for VPN container.")

            # Fetch Data via Page Request (to leverage existing browser session)
            xsrf = next((c['value'] for c in cookies if c['name'] == 'XSRF-TOKEN'), None)
            from urllib.parse import unquote
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "X-XSRF-TOKEN": unquote(xsrf) if xsrf else "",
                "Content-Type": "application/json",
            }
            
            # API Hits
            surveys_resp = await page.request.post(
                f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                data=json.dumps({"pageNumber": 0, "pageSize": 100, "sortBy": "CREATED_AT", "sortDirection": "DESC", "keywordSearch": ""}),
                headers=headers, timeout=15000
            )
            prov_resp = await page.request.get(f"{TARGET_URL}/region/api/v1/region/level1?groupId=82af087a-d063-48b9-8633-71c84c4e7422", timeout=15000)
            
            surveys_data = await surveys_resp.json()
            prov_data = await prov_resp.json()
            
            items = surveys_data.get("data", {}).get("content", [])
            surveys = [{"id": s.get("id"), "name": s.get("name") or s.get("surveyName", "")} for s in items]
            
            # Clean provinces: filter empty, handle duplicates with same fullCode
            raw_provinces = prov_data.get("data", [])
            provinces_map = {}
            for r in raw_provinces:
                fcode = r.get("fullCode")
                name = r.get("name", "").strip()
                if not fcode or not name: continue
                # Prefer name without brackets if both exist
                if fcode not in provinces_map or "[" not in name:
                    provinces_map[fcode] = {"id": r.get("id"), "name": name, "fullCode": fcode}
            
            provinces = sorted(list(provinces_map.values()), key=lambda x: x["fullCode"])

            timings["sso_login_ms"] = int((time.perf_counter() - t_browser) * 1000)
            timings["total_ms"] = int((time.perf_counter() - start_total) * 1000)
            result = {"surveys": surveys, "provinces": provinces}
            try:
                with get_session() as db_write:
                    from db.repository import set_system_setting
                    set_system_setting(db_write, CACHE_KEY_GLOBAL, json.dumps(result))
                    print(f"   ✅ [Lookup] USER CACHE UPDATED for {req.sso_username} (Browser Path).")
            except Exception as cache_err:
                print(f"   ⚠️ [Lookup] Failed to update user cache: {cache_err}")

            result["debug_timings"] = timings
            return result
        finally:
            await browser.close()


@router.post("/lookup/kabupaten")
async def lookup_kabupaten(req: KabupatenLookupRequest):
    """Fast kabupaten lookup using Storage State."""
    await ensure_connected()
    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
    CACHE_KEY  = f"sso_state_{req.sso_username}"
    
    # PHASE 1: Try with Storage State (Fast Path)
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
                    
                    # Hit API directly with Referer and groupId
                    print(f"   🚀 [Lookup] Trying Fast API hit for kabupaten (Prov: {req.prov_full_code})...")
                    GROUP_ID = "82af087a-d063-48b9-8633-71c84c4e7422"
                    resp = await page.request.get(
                        f"{TARGET_URL}/region/api/v1/region/level2?groupId={GROUP_ID}&level1FullCode={req.prov_full_code}", 
                        timeout=10000,
                        headers={"Referer": f"{TARGET_URL}/survey/new.html"}
                    )
                    
                    if resp.status == 200:
                        data = await resp.json()
                        kab = [{"id": r.get("id"), "name": r.get("name", ""), "fullCode": r.get("fullCode", "")} for r in data.get("data", [])]
                        print(f"   ✅ [Lookup] Fast API hit success. Found {len(kab)} kabupaten.")
                        await browser.close()
                        return {"kabupaten": kab}
                    else:
                        print(f"   ⚠️ [Lookup] Fast API hit failed (HTTP {resp.status}).")
                    await browser.close()
            except Exception as e:
                print(f"   ❌ [Lookup] Fast API exception: {str(e)}")

    # PHASE 2: Fallback to Full Login (Resilient Path)
    print(f"   🔄 [Lookup] Falling back to full login for kabupaten lookup...")
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await launch_stealth_browser(p)
        context = await new_stealth_context(browser)
        try:
            page = await context.new_page()
            success, _, err_msg = await auto_login(page, req.sso_username, req.sso_password)
            if not success:
                raise HTTPException(status_code=401, detail=f"Login gagal: {err_msg}")
            
            # Navigate to mature session
            await page.goto(f"{TARGET_URL}/survey/list.html", wait_until="networkidle", timeout=20000)
            
            # Hit API with groupId
            GROUP_ID = "82af087a-d063-48b9-8633-71c84c4e7422"
            resp = await page.request.get(
                f"{TARGET_URL}/region/api/v1/region/level2?groupId={GROUP_ID}&level1FullCode={req.prov_full_code}", 
                timeout=15000,
                headers={"Referer": f"{TARGET_URL}/survey/new.html"}
            )
            
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=f"Gagal mengambil data kabupaten: HTTP {resp.status}")
                
            data = await resp.json()
            kab = [{"id": r.get("id"), "name": r.get("name", ""), "fullCode": r.get("fullCode", "")} for r in data.get("data", [])]
            
            # Save new state for next time
            state = await context.storage_state()
            with get_session() as db:
                from db.repository import set_system_setting
                set_system_setting(db, CACHE_KEY, json.dumps(state))
                
            return {"kabupaten": kab}
        finally:
            await browser.close()
@router.post("/vpn/auto-fetch")
async def vpn_auto_fetch():
    """Endpoint for VPN container to trigger a cookie refresh using ENV credentials."""
    vpn_user = os.getenv("VPN_USER")
    vpn_pass = os.getenv("VPN_PASS")
    
    if not vpn_user or not vpn_pass:
        return {"success": False, "message": "VPN_USER/VPN_PASS not set in ENV"}
    
    from auth import fetch_vpn_cookie, sync_cookie_to_db
    import asyncio
    
    # Run in background to avoid blocking the VPN container's HTTP request
    async def run_fetch():
        print(f"🔄 [API] VPN container requested auto-fetch for {vpn_user}...")
        cookie = await fetch_vpn_cookie(vpn_user, vpn_pass)
        if cookie:
            await sync_cookie_to_db(cookie)
            print("✅ [API] VPN Auto-fetch success.")
        else:
            print("❌ [API] VPN Auto-fetch failed.")
            
    asyncio.create_task(run_fetch())
    return {"success": True, "message": "Auto-fetch triggered in background"}
