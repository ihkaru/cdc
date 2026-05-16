
import asyncio
import os
import json
import sys
import re
from urllib.parse import urlparse

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "rpa/src"))

from db.connection import get_session
from db.models import SystemSettings, Assignment
from api_client import FasihApiClient
from sqlalchemy import select

async def test_proxy():
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
    match = re.search(r'https://bucket1\.cloud\.bps\.go\.id/([^?"]+)', raw_json)
    if match:
        path = match.group(1)
    else:
        print(f"No URL found in assignment data! Raw: {raw_json[:200]}")
        return
    
    print(f"Testing Proxy for path: {path}")
    
    async with FasihApiClient(cookies) as api:
        # Try proxy view
        proxy_url = f"https://fasih-sm.bps.go.id/assignment-general/api/image/view?path={path}"
        print(f"   🔄 [Proxy] Requesting URL: {proxy_url}")
        
        headers = api._get_headers()
        async with await api.create_session() as session:
            async with session.get(proxy_url, headers=headers) as resp:
                print(f"   📊 Status: {resp.status}")
                print(f"   📄 Content-Type: {resp.headers.get('Content-Type')}")
                
                if resp.status == 200:
                    content = await resp.read()
                    print(f"   ✅ SUCCESS! Received {len(content)} bytes.")
                else:
                    text = await resp.text()
                    print(f"   ❌ FAILED! Body: {text[:200]}")

if __name__ == "__main__":
    asyncio.run(test_proxy())
