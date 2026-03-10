import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from auth import auto_login
from pages.survey_navigator import navigate_to_data_tab
from pages.filter_rotator import open_filter_sidebar, select_region_dropdown

async def capture_playload():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"], headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print("Logging in...")
        await auto_login(page, "ihzakarunia", "Fikrizaki2!")

        print("Navigating to survey data...")
        survey_id = "83f6053d-2120-4e7a-b322-d350bb975dd0"
        await navigate_to_data_tab(page, survey_id)
        
        # open filter
        print("Opening filter...")
        await open_filter_sidebar(page)

        print("Selecting region...")
        await select_region_dropdown(page, "region1Id", "[61] KALIMANTAN BARAT")
        await select_region_dropdown(page, "region2Id", "[04] MEMPAWAH")

        captured = None
        
        async def handle_request(req):
            nonlocal captured
            if "datatable-all-user-survey-periode" in req.url and req.method == "POST":
                captured = req.post_data
                with open("/tmp/fasih_payload.json", "w") as f:
                    f.write(captured)
                print("Payload captured! length:", len(captured))

        page.on("request", handle_request)

        # Select pencacah!
        print("Selecting pencacah via UI...")
        try:
            await page.click("ngx-select[name='pencacah']")
            await page.wait_for_selector("a.ngx-select__item:nth-child(2)")
            await page.click("a.ngx-select__item:nth-child(2)")
            print("Pencacah selected.")
        except Exception as e:
            print(f"Error selecting pencacah: {e}")

        print("Submitting filter (should trigger datatable)...")
        # Trigger datatable
        await page.click("button:has-text('Terapkan')")
        
        print("Waiting for API...")
        for _ in range(10):
            await page.wait_for_timeout(1000)
            if captured: break
            
        await browser.close()
        
        if captured:
            print(captured[:200])
        else:
            print("Failed to capture payload.")

if __name__ == "__main__":
    asyncio.run(capture_playload())
