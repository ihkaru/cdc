import aiohttp
import os

TARGET_URL = "https://fasih-sm.bps.go.id"


async def test_api():
    async with aiohttp.ClientSession() as session:
        # 1. Login to get SSO Cookie
        # We will just borrow the cookie from the container!
        cookie_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../tmp/new_vpn_cookie.txt")
        )
        if not os.path.exists(cookie_file):
            print(f"No cookie file found at {cookie_file}!")
            return

        with open(cookie_file, "r") as f:
            cookie_str = f.read().strip()

        session.cookie_jar.update_cookies({"SVPNCOOKIE": cookie_str})

        # We need a JSESSIONID to hit FASIH directly, not just SVPNCOOKIE!
        # Ah wait, let's use the local docker API instead to run the test!
        print("Instead of doing this manually, let's use the container's auth!")


if __name__ == "__main__":
    pass
