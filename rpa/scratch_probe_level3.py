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
        survey_name = "GC PBI 2026 [TAHAP 2] - PENDATAAN"
        survey_id = await api.get_survey_id(survey_name)
        period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)

        prov_uuid, region_filter, kab_full_code, region_group_id = await api.get_region_metadata(
            "[61] KALIMANTAN BARAT", "[04] MEMPAWAH", survey_id
        )
        print(f"survey_id={survey_id}, region_group_id={region_group_id}, kab_full_code={kab_full_code}")

        # Test query level3
        url = f"region/api/v1/region/level3?groupId={region_group_id}&level2FullCode={kab_full_code}"
        print(f"Querying GET {url}...")
        try:
            # We call the session directly to get raw response and headers
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
