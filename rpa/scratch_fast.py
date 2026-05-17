import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-http2']
        )
        page = await browser.new_page()
        print("Navigating...")
        try:
            await page.goto("https://akses.bps.go.id/remote/login", wait_until="commit", timeout=20000)
            print("Commit reached! Waiting 3s...")
            await asyncio.sleep(3)
            print(f"URL: {page.url}")
            body_text = await page.inner_text("body")
            print("--- BODY TEXT ---")
            print(body_text)
            print("-----------------")
        except Exception as e:
            print(f"Error: {e}")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
