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

    api = FasihApiClient(cookies_dict)
    
    survey_id = "83f6053d-2120-4e7a-b322-d350bb975dd0"
    async with await api.create_session() as session:
        url = f"https://fasih-sm.bps.go.id/survey/api/v1/surveys/{survey_id}"
        async with session.get(url, headers={"Accept": "application/json"}) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Body: {text[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
