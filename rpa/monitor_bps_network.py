import asyncio
import os
import sys

from playwright.async_api import async_playwright

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "rpa/src"))


async def monitor_bps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Load cookies from DB if available to skip login
        # For simplicity, I'll just try to use the existing ones if I can inject them
        # But wait, better to just log in fresh to be sure.

        # USER: ihzakarunia@bps.go.id / Fikrizaki2!
        print("Logging in...")
        await page.goto("https://fasih-sm.bps.go.id/login")
        await page.fill("input[name='username']", "ihzakarunia@bps.go.id")
        await page.fill("input[name='password']", "Fikrizaki2!")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/dashboard**", timeout=60000)
        print("Logged in successfully.")

        # Capture all requests to image/presigned
        captured_urls = []
        page.on(
            "response",
            lambda response: (
                captured_urls.append(response.url) if "presigned" in response.url or "image" in response.url else None
            ),
        )

        target_id = "20ae3fe1-93bc-467e-862b-e1c069683d85"
        detail_url = f"https://fasih-sm.bps.go.id/assignment/detail/{target_id}"
        print(f"Navigating to detail: {detail_url}")

        await page.goto(detail_url)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5)  # Wait for async photo loads

        print("\n--- CAPTURED RELEVANT RESPONSES ---")
        for url in captured_urls:
            if "bps.go.id" in url:
                print(f"URL: {url[:120]}...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(monitor_bps())
