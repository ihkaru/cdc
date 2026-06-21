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
        setting = session.query(SystemSettings).filter(SystemSettings.key.like("sso_cookies_%")).first()
    cookies = json.loads(setting.value)
    if isinstance(cookies, dict) and "cookies" in cookies:
        cookies = cookies["cookies"]
    if isinstance(cookies, list):
        cookies = {c["name"]: c["value"] for c in cookies}

    async with FasihApiClient(cookies) as api:
        # Query detail for a valid assignment ID
        assignment_id = "00019c4a-e299-47c1-ba74-80bd5a33d7b8"
        url = f"app/api/assignment-general/api/assignment/get-by-assignment-id?assignmentId={assignment_id}"

        body = await api._request("GET", url)
        print("Response structure keys:")
        if body:
            print(f"success: {body.get('success')}")
            print(f"data type: {type(body.get('data'))}")
            if body.get("data"):
                data = body.get("data")
                print(f"data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                print(f"data id value: {data.get('id') if isinstance(data, dict) else 'N/A'}")
        else:
            print("Response is None")


if __name__ == "__main__":
    asyncio.run(probe())
