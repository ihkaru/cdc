import os
import asyncio
from fastapi import APIRouter, HTTPException

from schemas import LookupRequest, KabupatenLookupRequest, ProbeRequest
from auth import auto_login
from pages.survey_navigator import find_survey_id, navigate_to_data_tab
from pages.filter_rotator import open_filter_sidebar, select_region_dropdown, click_filter_data
from pages.assignment_page import inject_page_size_1000
from connectivity import ensure_connected

router = APIRouter()

@router.post("/lookup/metadata")
async def lookup_metadata(req: LookupRequest):
    """
    Login ke FASIH via Playwright, lalu fetch:
    - Daftar semua survey (Pencacahan)
    - Daftar semua provinsi

    Digunakan oleh wizard Add Survey di dashboard.
    Membutuhkan ~15 detik karena harus login SSO Keycloak.
    """
    from playwright.async_api import async_playwright
    import aiohttp

    # Proactive self-healing
    await ensure_connected()

    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
    GROUP_ID   = "82af087a-d063-48b9-8633-71c84c4e7422"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        try:
            page = await context.new_page()
            login_ok = await auto_login(page, req.sso_username, req.sso_password)
            if not login_ok:
                raise HTTPException(status_code=401, detail="Login FASIH gagal. Periksa username/password.")

            # Ambil cookies dari Playwright
            pw_cookies = await context.cookies()
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            for c in pw_cookies:
                cookie_jar.update_cookies({c["name"]: c["value"]})

            # SSL bypass untuk koneksi VPN internal
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"{TARGET_URL}/",
                "Origin": TARGET_URL,
                "X-Requested-With": "XMLHttpRequest",
            }
            if pw_cookies:
                for c in pw_cookies:
                    if c["name"] == "XSRF-TOKEN":
                        headers["X-XSRF-TOKEN"] = c["value"]
                        break

            connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=50)
            async with aiohttp.ClientSession(
                cookie_jar=cookie_jar,
                connector=connector,
                headers=headers,
            ) as session:
                # === Fetch survey list (all pages) ===
                surveys = []
                page_number = 0
                while True:
                    try:
                        async with session.post(
                            f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan",
                            json={
                                "pageNumber": page_number,
                                "pageSize": 50,
                                "sortBy": "CREATED_AT",
                                "sortDirection": "DESC",
                                "keywordSearch": "",
                            },
                        ) as resp:
                            if resp.status != 200:
                                raise HTTPException(
                                    status_code=resp.status, 
                                    detail=f"FASIH returned status {resp.status}. VPN connection may be unstable."
                                )
                            
                            content_type = resp.headers.get("Content-Type", "")
                            if "application/json" not in content_type:
                                # Likely redirected to login page (HTML)
                                raise HTTPException(
                                    status_code=503, 
                                    detail="FASIH di-redirect ke halaman login (Access Denied). Pastikan VPN Cookie sudah di-update di Dashboard."
                                )

                            data = await resp.json()
                            items = data.get("data", {}).get("content", [])
                            for s in items:
                                surveys.append({
                                    "id":   s.get("id"),
                                    "name": s.get("name") or s.get("surveyName", ""),
                                })
                            total_pages = data.get("totalPage", 1)
                            if page_number >= total_pages - 1 or not items:
                                break
                            page_number += 1
                    except aiohttp.ClientError as e:
                        raise HTTPException(status_code=503, detail=f"Gagal menghubungi FASIH (Network Error): {str(e)}")

                # === Fetch province list ===
                provinces = []
                async with session.get(
                    f"{TARGET_URL}/region/api/v1/region/level1?groupId={GROUP_ID}",
                ) as resp:
                    data = await resp.json()
                    for r in data.get("data", []):
                        provinces.append({
                            "id":       r.get("id"),
                            "name":     r.get("name", ""),
                            "fullCode": r.get("fullCode", ""),
                        })

        finally:
            await browser.close()

    return {
        "surveys":   surveys,
        "provinces": provinces,
    }


@router.post("/lookup/kabupaten")
async def lookup_kabupaten(req: KabupatenLookupRequest):
    """
    Fetch daftar kabupaten untuk satu provinsi.
    Menggunakan SSO creds yang sama — jika sesi Keycloak masih valid
    proses login akan sangat cepat (<5 detik).
    """
    from playwright.async_api import async_playwright
    import aiohttp

    # Proactive self-healing
    await ensure_connected()

    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
    GROUP_ID   = "82af087a-d063-48b9-8633-71c84c4e7422"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        try:
            page = await context.new_page()
            login_ok = await auto_login(page, req.sso_username, req.sso_password)
            if not login_ok:
                raise HTTPException(status_code=401, detail="Login FASIH gagal.")

            pw_cookies = await context.cookies()
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            for c in pw_cookies:
                cookie_jar.update_cookies({c["name"]: c["value"]})

            # SSL bypass untuk koneksi VPN internal
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"{TARGET_URL}/",
                "Origin": TARGET_URL,
                "X-Requested-With": "XMLHttpRequest",
            }
            if pw_cookies:
                for c in pw_cookies:
                    if c["name"] == "XSRF-TOKEN":
                        headers["X-XSRF-TOKEN"] = c["value"]
                        break

            connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=50)
            async with aiohttp.ClientSession(
                cookie_jar=cookie_jar,
                connector=connector,
                headers=headers,
            ) as session:
                kabupaten = []
                try:
                    async with session.get(
                        f"{TARGET_URL}/region/api/v1/region/level2"
                        f"?groupId={GROUP_ID}&level1FullCode={req.prov_full_code}",
                    ) as resp:
                        if resp.status != 200:
                            raise HTTPException(status_code=resp.status, detail=f"FASIH returned {resp.status}")
                        
                        content_type = resp.headers.get("Content-Type", "")
                        if "application/json" not in content_type:
                            raise HTTPException(status_code=503, detail="FASIH di-redirect ke login. Perlu refresh VPN Cookie.")

                        data = await resp.json()
                        for r in data.get("data", []):
                            kabupaten.append({
                                "id":       r.get("id"),
                                "name":     r.get("name", ""),
                                "fullCode": r.get("fullCode", ""),
                            })
                except aiohttp.ClientError as e:
                    raise HTTPException(status_code=503, detail=f"Network error: {str(e)}")

        finally:
            await browser.close()

    return {"kabupaten": kabupaten}


@router.post("/probe/datatable")
async def probe_datatable(req: ProbeRequest):
    """
    Probe: intercept ALL API responses during DataTable reload.
    Returns discovered endpoints + sample data for incremental sync analysis.
    """
    import json as json_mod
    from playwright.async_api import async_playwright

    captured = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        try:
            page = await context.new_page()

            login_ok = await auto_login(page, req.sso_username, req.sso_password)
            if not login_ok:
                raise HTTPException(status_code=500, detail="Login gagal")

            survey_id = await find_survey_id(page, req.survey_name)
            if not survey_id:
                raise HTTPException(status_code=404, detail=f"Survey '{req.survey_name}' not found")
            await navigate_to_data_tab(page, survey_id)

            async def on_response(response):
                url = response.url
                content_type = response.headers.get("content-type", "")
                if response.status == 200 and ("json" in content_type or "/api/" in url):
                    try:
                        body = await response.json()
                        sample = {}
                        if isinstance(body, dict):
                            for k, v in body.items():
                                if isinstance(v, list) and len(v) > 0:
                                    sample[k] = {
                                        "_type": "array",
                                        "_length": len(v),
                                        "_first_item_keys": list(v[0].keys()) if isinstance(v[0], dict) else type(v[0]).__name__,
                                        "_first_item": v[0] if len(json_mod.dumps(v[0], default=str)) < 2000 else "[too large]",
                                    }
                                else:
                                    sample[k] = {k2: type(v2).__name__ for k2, v2 in v.items()} if isinstance(v, dict) else v
                        else:
                            sample = {"_raw_type": type(body).__name__}

                        captured.append({
                            "url": url,
                            "method": response.request.method,
                            "status": response.status,
                            "sample": sample,
                        })
                    except:
                        captured.append({
                            "url": url,
                            "method": response.request.method,
                            "status": response.status,
                            "sample": "[parse error]",
                        })

            page.on("response", on_response)

            await open_filter_sidebar(page)
            await asyncio.sleep(1)

            if req.filter_provinsi:
                await select_region_dropdown(page, "ngx-select[name='region1Id']", req.filter_provinsi)
                await asyncio.sleep(2)
            if req.filter_kabupaten:
                await select_region_dropdown(page, "ngx-select[name='region2Id']", req.filter_kabupaten)
                await asyncio.sleep(2)

            await click_filter_data(page)
            await asyncio.sleep(3)

            await inject_page_size_1000(page)
            await asyncio.sleep(3)

            page.remove_listener("response", on_response)

        finally:
            await browser.close()

    return {"total_captured": len(captured), "endpoints": captured}
