import asyncio
from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright...")
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-http2',
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="en-US",
            timezone_id="Asia/Jakarta"
        )
        page = await context.new_page()
        
        print("Navigating to akses.bps.go.id/remote/login...")
        try:
            await page.goto("https://akses.bps.go.id/remote/login", wait_until="commit", timeout=30000)
            print(f"Navigation complete! Current URL: {page.url}")
            await asyncio.sleep(5)
            
            # Wait for SAML button
            print("Waiting for SSO/SAML button...")
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
            print("SSO/SAML button found! Clicking it...")
            await page.click(combined_selector, force=True)
            
            print("Clicked SSO button. Waiting 10s for Keycloak transition...")
            for i in range(1, 11):
                await asyncio.sleep(1)
                print(f"  Url after {i}s: {page.url}")
                
            # Take a screenshot to see what's on the screen
            await page.screenshot(path="sso_current.png")
            print("Screenshot saved to sso_current.png")
            
            content = await page.content()
            with open("sso_current.html", "w") as f:
                f.write(content)
            print("Page HTML saved to sso_current.html")
            
        except Exception as e:
            print(f"Error during flow: {e}")
            try:
                await page.screenshot(path="sso_error.png")
                print("Error screenshot saved to sso_error.png")
            except:
                pass
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
