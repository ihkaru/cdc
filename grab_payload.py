import asyncio
import os
import json
from playwright.async_api import async_playwright
import time

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

async def capture_datatable():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Intercept and log requests
        async def handle_request(request):
            if "datatable-all-user-survey-periode" in request.url and request.method == "POST":
                print("\n\n=== FULL DATATABLE PAYLOAD ===")
                print(request.post_data)
                print("==============================\n\n")
                
                # Write to file
                with open("full_payload.json", "w") as f:
                    f.write(request.post_data)
                
        page.on("request", handle_request)
        
        # 1. Login
        print("Logging in...")
        await page.goto(f"{TARGET_URL}/")
        try:
            await page.get_by_text("Login SSO BPS").click()
            await page.wait_for_url("**/auth/realms/bps/protocol/openid-connect/auth*")
            await page.locator("#username").fill(os.getenv("sso_username"))
            await page.locator("#password").fill(os.getenv("sso_password"))
            await page.locator("#kc-login").click()
            await page.wait_for_url(f"**{TARGET_URL}/dashboard**")
            print("Login success")
        except Exception as e:
            pass
            
        # 2. Go to Sakernas Survey tab directly
        # ID is c3274ff3-ea58-4309-9980-ebed0c566f9d
        print("Opening survey page...")
        await page.goto(f"{TARGET_URL}/survey-collection/collect/83f6053d-2120-4e7a-b322-d350bb975dd0")
        
        print("Waiting for network...")
        await asyncio.sleep(10) # wait for the table to load
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_datatable())
