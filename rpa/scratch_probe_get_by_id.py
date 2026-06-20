import asyncio
import json

from src.api_client import FasihApiClient
from src.db.connection import get_session, init_db
from src.db.models import SystemSettings


async def probe():
    init_db()
    session = get_session()
    setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
    if not setting:
        print("No cookies found in DB")
        return
    cookies = json.loads(setting.value)

    async with FasihApiClient(cookies) as api:
        # We query the probe URL without parameters
        url = "app/api/assignment-general/api/assignment/get-by-assignment-id"
        print(f"Querying GET {url}...")
        try:
            headers = api._get_headers()
            async with api.session.get(f"https://fasih-sm.bps.go.id/{url}", headers=headers) as resp:
                print(f"Status: {resp.status}")
                print(f"Headers: {dict(resp.headers)}")
                text = await resp.text()
                print("Body preview (first 1000 chars):")
                print(text[:1000])
        except Exception as e:
            print(f"Failed: {e}")


if __name__ == "__main__":
    asyncio.run(probe())
