
import asyncio
import os
import json
import sys
import re
import time

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "rpa/src"))

from db.connection import get_session
from db.models import SystemSettings, Assignment
from api_client import FasihApiClient
from sqlalchemy import select

async def test_refresh():
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
    
    print(f"Testing refresh for assignment {assignment.id} WITH CACHE BUSTER")
    
    async with FasihApiClient(cookies) as api:
        # Try detail fetch with cache buster
        ts = int(time.time() * 1000)
        url = f"https://fasih-sm.bps.go.id/assignment-general/api/assignment/get-by-id-with-data-for-scm?id={assignment.id}&_t={ts}"
        
        print(f"   🔄 [API] Requesting URL: {url}")
        
        headers = api._get_headers()
        async with await api.create_session() as session:
            async with session.get(url, headers=headers) as resp:
                body = await resp.json()
                detail = body.get("data")
        
        # Extract URLs
        detail_str = json.dumps(detail)
        urls = re.findall(r'https://bucket1\.cloud\.bps\.go\.id/[^"]+', detail_str)
        
        print("\n--- RESULTS ---")
        if not urls:
            print("No BPS Cloud URLs found in detail JSON.")
        for url in urls[:3]:
            print(f"URL: {url[:100]}...")
            match = re.search(r"X-Amz-Date=(\d{8})", url)
            if match:
                print(f"   Date: {match.group(1)}")
            else:
                print("   Date: NOT FOUND")

if __name__ == "__main__":
    asyncio.run(test_refresh())
