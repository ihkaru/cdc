"""
Assignment Page — Intercept DataTable API untuk mendapatkan metadata assignment
"""
import os
import asyncio
from typing import List, Dict
from playwright.async_api import Page, Response

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")


async def inject_page_size_1000(page: Page):
    """
    Inject option '1000' ke select page size DataTable, lalu pilih.
    Ini memaksa datatable meload semua data dalam 1 API call (jika di bawah limit).
    """
    await page.evaluate(f"""() => {{
        const select = document.querySelector('select[name="assignmentDatatable_length"]');
        if (select) {{
            // Tambahkan option 1000 jika belum ada
            let exists = false;
            for (const opt of select.options) {{
                if (opt.value === '1000') {{ exists = true; break; }}
            }}
            if (!exists) {{
                const option = document.createElement('option');
                option.value = '1000';
                option.text = '1000';
                select.appendChild(option);
            }}
            // Pilih 1000
            select.value = '1000';
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    }}""")
    
    # Tunggu DataTable processing
    try:
        await page.wait_for_selector("div#assignmentDatatable_processing", state="visible", timeout=2000)
    except:
        pass


async def get_all_assignments_metadata(page: Page) -> List[Dict]:
    """
    Intercept API `/analytic/api/v2/assignment/datatable-all-user-survey-periode`
    saat DataTable reload, untuk mendapatkan metadata assignment (id, dateModified).
    """
    metadata_list = []
    response_captured = asyncio.Event()

    async def on_response(response: Response):
        if "datatable-all-user-survey-periode" in response.url and response.status == 200:
            if response.request.method == "OPTIONS":
                return
            try:
                body = await response.json()
                if isinstance(body, dict) and "searchData" in body:
                    search_data = body["searchData"]
                    if isinstance(search_data, list):
                        print(f"   📡 Intercepted API! Found {len(search_data)} records in searchData.")
                        for item in search_data:
                            if isinstance(item, dict) and "id" in item:
                                metadata_list.append({
                                    "id": item.get("id"),
                                    "dateModified": item.get("dateModified"),
                                })
                    if not response_captured.is_set():
                        response_captured.set()
            except Exception as e:
                print(f"   ⚠️ Error parsing datatable API response: {e}")

    # Listen to response
    page.on("response", on_response)

    try:
        # Panggil API ulang karena kadang call pertama adalah dari `filter_rotator`
        print("   📐 Menginject page size 1000 untuk fetch metadata sekaligus...")
        await inject_page_size_1000(page)
        
        # Wait for the API response
        try:
            await asyncio.wait_for(response_captured.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            print("   ⚠️ Timeout menunggu response datatable API.")
            
        try:
            await page.wait_for_selector("div#assignmentDatatable_processing", state="hidden", timeout=15000)
        except:
            pass
            
    finally:
        page.remove_listener("response", on_response)

    print(f"   📋 Mendapatkan {len(metadata_list)} metadata assignment dari DataTable API")
    return metadata_list
