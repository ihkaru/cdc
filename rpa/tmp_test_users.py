import asyncio
import os
import aiohttp
import ssl
from dotenv import load_dotenv

load_dotenv()
TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
COOKIE = os.getenv("VPN_COOKIE", "")

async def main():
    period_id = "a4f9069c-752a-44c7-ae6c-f58f1721aed4"
    role_id = "39e11721-114e-4fe5-a9a9-dc8eb8ed3697"
    region_code = "6104"
    
    url = f"{TARGET_URL}/survey/api/v1/survey-period-role-users/region?surveyPeriodId={period_id}&surveyRoleId={role_id}&regionCode={region_code}"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Cookie": COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://fasih-sm.bps.go.id/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(ssl=ssl_ctx)) as session:
        async with session.get(url) as resp:
            text = await resp.text()
            print(f"Status: {resp.status}")
            print(text[:1000])

if __name__ == "__main__":
    asyncio.run(main())
