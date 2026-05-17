import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-http2',
            ]
        )
        page = await browser.new_page()
        print("Navigating...")
        try:
            await page.goto("https://akses.bps.go.id/remote/login", wait_until="commit", timeout=20000)
            print("Commit reached! Waiting 5s for scripts to stabilize...")
            await asyncio.sleep(5)
            
            saml_selectors = [
                "#saml-login-bn", 
                ".btn-saml", 
                "button:has-text('Login SSO')", 
                "button:has-text('SAML')",
                "a[href*='/oauth2/authorization/ics']",
                "a:has-text('Login SSO BPS')"
            ]
            combined_selector = ", ".join(saml_selectors)
            await page.wait_for_selector(combined_selector, timeout=10000)
            print("Clicking SSO button...")
            await page.click(combined_selector, force=True)
            
            print("SSO Clicked! Monitoring URL transition for 15 seconds...")
            for i in range(1, 16):
                await asyncio.sleep(1)
                print(f"[{i}s] URL: {page.url}")
                if "sso.bps.go.id" in page.url:
                    print("Reached Keycloak SSO!")
                    body_text = await page.inner_text("body")
                    print("--- SSO BODY ---")
                    print(body_text[:500])
                    print("----------------")
                    break
        except Exception as e:
            print(f"Error: {e}")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
