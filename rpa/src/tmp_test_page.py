import asyncio
import os
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
        login_ok, cookies_dict = await auto_login(page, username, password)
        await browser.close()

    api = FasihApiClient(cookies_dict)
    
    survey_id = "83f6053d-2120-4e7a-b322-d350bb975dd0"
    period_id = "a4f9069c-752a-44c7-ae6c-f58f1721aed4"
    prov_uuid = "d73f28ca-cef3-4c5e-b0f8-6b75d434cf07"
    kab_uuid = "ef07bdb0-c279-4bf8-82ed-9c4b0896ea8e"
    
    async with await api.create_session() as session:
        url = "https://fasih-sm.bps.go.id/analytic/api/v2/assignment/datatable-all-user-survey-periode"
        
        page_start = 1000
        page_size = 1000
        payload = {
            "draw": 2,
            "columns": [{"data": "id", "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}}],
            "order": [],
            "start": page_start,
            "length": page_size,
            "search": {"value": "", "regex": False},
            "assignmentExtraParam": {
                "assignmentStatusId": "",
                "userId": "",
                "surveyPeriodId": period_id,
                "isTarikSample": "",
                "region1Id": prov_uuid,
                "region2Id": kab_uuid,
                "regionGroupId": "fe31ec30-417d-4797-b97f-2d98a902dc03",
                "filterTargetType": "TARGET_ONLY",
                "regionId": "",
                "currentUserId": ""
            }
        }
        
        async with session.post(url, json=payload, headers={"Accept": "application/json"}) as resp:
            data = await resp.json()
            search_data = data.get("searchData", [])
            print(f"Start: {page_start}")
            print(f"Total Hit: {data.get('totalHit')}")
            print(f"Fetched: {len(search_data)}")

if __name__ == "__main__":
    asyncio.run(main())
