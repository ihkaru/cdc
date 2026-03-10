import asyncio
import os
import aiohttp
import ssl
from dotenv import load_dotenv
import json

load_dotenv()
TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
COOKIE = os.getenv("VPN_COOKIE", "")

async def main():
    survey_id = "83f6053d-2120-4e7a-b322-d350bb975dd0"
    
    url = f"{TARGET_URL}/survey/api/v1/survey/{survey_id}"
    
    headers = {
        "Accept": "application/json",
        "Cookie": COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(ssl=ssl_ctx)) as session:
        async with session.get(url) as resp:
            data = await resp.json()
            survey = data.get("data", {})
            print("Keys in survey:", survey.keys())
            print("regionGroupId:", survey.get("regionGroupId"))

if __name__ == "__main__":
    asyncio.run(main())
