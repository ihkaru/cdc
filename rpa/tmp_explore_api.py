import asyncio
import json
import logging
from playwright.async_api import async_playwright, Request, Response
from config.settings import Settings
from src.auth import auto_login
from src.pages.survey_navigator import find_survey_id, navigate_to_data_tab

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def log_request(request: Request):
    if request.resource_type in ["fetch", "xhr"]:
        logging.info(f"➡️ REQUEST: [{request.method}] {request.url}")
        try:
            post_data = request.post_data
            if post_data:
                if "datatable-all-user-survey-periode" in request.url:
                    logging.info(f"   === FULL PAYLOAD ===\n{post_data}\n======================")
                else:
                    logging.info(f"   Payload: {post_data[:200]}...")
        except:
            pass

async def log_response(response: Response):
    if response.request.resource_type in ["fetch", "xhr"]:
        logging.info(f"⬅️ RESPONSE: [{response.status}] {response.url}")
        if response.status == 200 and "survey-collection" in response.url:
            try:
                body = await response.text()
                logging.info(f"   Body: {body[:200]}...")
            except:
                pass

async def explore_api():
    settings = Settings.from_env()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Attach listeners
        page.on("request", log_request)
        page.on("response", log_response)
        
        logging.info("Starting API Exploration...")
        
        login_ok = await auto_login(page, settings.sso_username, settings.sso_password)
        if not login_ok:
            logging.error("Login failed")
            return
            
        survey_id = await find_survey_id(page, settings.survey_name)
        if not survey_id:
            logging.error("Survey not found")
            return
            
        await navigate_to_data_tab(page, survey_id)
        
        logging.info("Waiting 30 seconds to capture interactions...")
        await asyncio.sleep(30)
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_api())
