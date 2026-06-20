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
        survey_name = "SENSUS EKONOMI 2026 - UB"
        survey_id = await api.get_survey_id(survey_name)
        period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)

        region_code = "6104"  # Mempawah

        print(f"\n--- Probing GET survey-period-role-users/region for regionCode={region_code} ---")
        for role_id in role_ids:
            path = f"survey/api/v1/survey-period-role-users/region?surveyPeriodId={period_id}&surveyRoleId={role_id}&regionCode={region_code}"
            try:
                body = await api._request("GET", path)
                if body and body.get("data"):
                    print(f"Role {role_id}: SUCCESS. Found {len(body['data'])} users")
                    for user in body["data"]:
                        print(
                            f"  - User: {user.get('fullname')} ({user.get('username')}), isPencacah: {user.get('isPencacah')}"
                        )
                else:
                    print(f"Role {role_id}: Empty or null")
            except Exception as e:
                print(f"Role {role_id}: FAILED - {e}")


if __name__ == "__main__":
    asyncio.run(probe())
