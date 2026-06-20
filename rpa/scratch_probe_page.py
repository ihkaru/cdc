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
        # Let's use the survey config we just ran: SENSUS EKONOMI 2026 - UB
        survey_name = "SENSUS EKONOMI 2026 - UB"
        survey_id = await api.get_survey_id(survey_name)
        print(f"Survey ID: {survey_id}")

        period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)
        print(f"Period ID: {period_id}, Role IDs: {role_ids}, Role Group ID: {role_group_id}")

        for page_num in [0, 1, 2]:
            dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_ids[0]}"
            payload = {
                "pageNumber": page_num,
                "pageSize": 200,
                "sortBy": "ID",
                "sortDirection": "ASC",
                "keywordSearch": "",
            }
            try:
                body = await api._request("POST", dt_url, json=payload)
                print(
                    f"PageNumber {page_num}: SUCCESS. Found {len(body.get('data', {}).get('searchData', [])) if body else 0} users"
                )
            except Exception as e:
                print(f"PageNumber {page_num}: FAILED - {e}")


if __name__ == "__main__":
    asyncio.run(probe())
