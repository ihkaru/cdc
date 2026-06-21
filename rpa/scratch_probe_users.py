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
        survey_name = "SENSUS EKONOMI 2026"
        survey_id = await api.get_survey_id(survey_name)
        period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)

        # Loop through all roles and try to find users using pageSize=100
        for role_id in role_ids:
            dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}"
            payload = {
                "pageNumber": 0,
                "pageSize": 100,
                "sortBy": "ID",
                "sortDirection": "ASC",
                "keywordSearch": "",
            }
            try:
                body = await api._request("POST", dt_url, json=payload)
                if body and body.get("data"):
                    users = body["data"].get("searchData", [])
                    total = body["data"].get("totalElements", 0)
                    print(f"Role: {role_id} -> SUCCESS, Found {len(users)} users (Total elements: {total})")
                    if users:
                        print(f"Sample user: {users[0]}")
            except Exception as e:
                print(f"Role: {role_id} -> FAILED - {e}")


if __name__ == "__main__":
    asyncio.run(probe())
