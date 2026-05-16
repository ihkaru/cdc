
import asyncio
import os
import json
import sys
import re

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "rpa/src"))

from db.connection import get_session
from db.models import SystemSettings, Assignment
from api_client import FasihApiClient
from sqlalchemy import select

async def test_cookie_s3():
    db = get_session()
    
    # Get cookies
    sso_setting = db.execute(select(SystemSettings).where(SystemSettings.key == "sso_cookies")).scalar_one_or_none()
    if not sso_setting:
        print("No cookies found!")
        return
    cookies = json.loads(sso_setting.value)
    
    # Get any assignment
    assignment = db.execute(select(Assignment).limit(1)).scalar_one_or_none()
    if not assignment:
        print("Assignment not found!")
        return
    
    # Find any URL in raw JSON
    raw_json = str(assignment.data_json)
    match = re.search(r'https://bucket1\.cloud\.bps\.go\.id/[^"]+', raw_json)
    if match:
        url = match.group(0)
    else:
        print("No URL found!")
        return
    
    print(f"Testing S3 Download with Cookies: {url[:100]}...")
    
    async with FasihApiClient(cookies) as api:
        headers = api._get_headers()
        # Add a very common User-Agent
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        async with await api.create_session() as session:
            # We don't need to strip params, just see if cookies help bypass 403
            async with session.get(url, headers=headers) as resp:
                print(f"   📊 Status: {resp.status}")
                if resp.status == 200:
                    content = await resp.read()
                    print(f"   ✅ SUCCESS! Received {len(content)} bytes.")
                else:
                    print(f"   ❌ FAILED! Still getting {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_cookie_s3())
