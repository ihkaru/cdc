import asyncio
import os
import sys
from api_client import FasihApiClient
from auth import auto_login
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def main():
    username = os.environ.get("sso_username")
    password = os.environ.get("sso_password")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Logging in...")
        login_ok, cookies_dict = await auto_login(page, username, password)
        await browser.close()

    if not login_ok:
        print("Login failed")
        return

    api = FasihApiClient(cookies_dict)

    survey_id = "83f6053d-2120-4e7a-b322-d350bb975dd0"
    period_id = "a4f9069c-752a-44c7-ae6c-f58f1721aed4"
    prov_uuid = "d73f28ca-cef3-4c5e-b0f8-6b75d434cf07"
    kab_uuid = "ef07bdb0-c279-4bf8-82ed-9c4b0896ea8e"
    
    print("\nFetching assignments directly...")
    data, error = await api.get_assignments_metadata(
        period_id=period_id,
        prov_uuid=prov_uuid,
        kab_uuid=kab_uuid,
        pengawas_id=None,
        pencacah_id=None
    )
    
    if error:
        print("Error:", error)
    else:
        print("Total fetched:", len(data))
        if data:
            print("First item:", data[0].get('id'))

if __name__ == "__main__":
    asyncio.run(main())
