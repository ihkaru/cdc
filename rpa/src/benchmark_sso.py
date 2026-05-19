import asyncio
import os
import sys
import time

from playwright.async_api import async_playwright

from auth import launch_stealth_browser, new_stealth_context, perform_sso_login

USERNAME = os.getenv("TEST_SSO_USERNAME", "ihzakarunia@bps.go.id")
PASSWORD = os.getenv("TEST_SSO_PASSWORD", "Fikrizaki2!")


async def run_benchmark():
    print("==================================================")
    print("🚀 BENCHMARK: SSO LOGIN POLLING SPEED")
    print("==================================================")

    t_start = time.time()

    # 1. Browser Launch
    print("\n1️⃣ Launching Browser...")
    t0 = time.time()
    async with async_playwright() as p:
        browser = await launch_stealth_browser(p)
        context = await new_stealth_context(browser)
        page = await context.new_page()
        t1 = time.time()
        print(f"   ⏱️ Browser launched in {t1 - t0:.2f}s")

        # 2. SSO Navigation
        print("\n2️⃣ Navigating to Portal & SSO (Using actual perform_sso_login)...")
        success, err_msg = await perform_sso_login(page, USERNAME, PASSWORD)
        t2 = time.time()

        if not success:
            print(f"   ❌ SSO Navigation Failed in {t2 - t1:.2f}s: {err_msg}")
            await browser.close()
            sys.exit(1)

        print(f"   ⏱️ SSO Navigation completed in {t2 - t1:.2f}s")

        # 3. Cookie Polling
        print("\n3️⃣ Polling for FASIH-SM Session Cookie (XSRF-TOKEN / laravel_session)...")
        polling_start = time.time()
        has_session = False
        attempts = 0

        while (time.time() - polling_start) < 30:
            attempts += 1
            cookies_list = await page.context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in cookies_list}
            has_session = any(name in cookies_dict for name in ["XSRF-TOKEN", "laravel_session"])

            if has_session:
                t_poll_done = time.time()
                print(f"   ✅ Session cookies captured on attempt {attempts}!")
                print(f"   ⏱️ Cookie polling took {t_poll_done - polling_start:.2f}s")
                break

            await asyncio.sleep(1)

        if not has_session:
            t_poll_done = time.time()
            print(f"   ❌ Polling timed out after {t_poll_done - polling_start:.2f}s")

        # 4. Total Time
        t_end = time.time()
        print("\n==================================================")
        print(f"🏁 TOTAL RAW SSO LOGIN TIME: {t_end - t_start:.2f}s")
        print("==================================================")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_benchmark())
