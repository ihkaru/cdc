import asyncio
import os
from api_client import FasihApiClient
from auth import auto_login
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import json

load_dotenv()

async def main():
    username = os.environ.get("sso_username")
    password = os.environ.get("sso_password")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Logging in...")
        login_ok, cookies_dict = await auto_login(page, username, password)
        await browser.close()

    api = FasihApiClient(cookies_dict)
    
    async with await api.create_session() as session:
        url = "https://fasih-sm.bps.go.id/survey/api/v1/surveys/datatable?surveyType=Pencacahan"
        payload = {"pageNumber":0,"pageSize":10,"sortBy":"CREATED_AT","sortDirection":"DESC","keywordSearch":""}
        async with session.post(url, json=payload, headers={"Accept": "application/json"}) as resp:
            data = await resp.json()
            survey0 = data.get("data", {}).get("content", [])[0]
            print(f"First survey ID: {survey0.get('id')}")
            print(f"Keys: {survey0.keys()}")
            print(f"regionGroupId: {survey0.get('regionGroupId')}")

if __name__ == "__main__":
    asyncio.run(main())
