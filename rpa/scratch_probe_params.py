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
        role_id = role_ids[0]

        # Test 1: Query parameters on POST
        print("\n--- Test 1: Query parameters on POST ---")
        dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}&pageNumber=1&pageSize=10"
        try:
            body = await api._request("POST", dt_url)
            print(f"Test 1 SUCCESS: Found {body.get('data', {}).get('totalElements') if body else 0} elements")
        except Exception as e:
            print(f"Test 1 FAILED: {e}")

        # Test 2: Form data on POST
        print("\n--- Test 2: Form data on POST ---")
        dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}"
        payload = {
            "pageNumber": 1,
            "pageSize": 10,
            "sortBy": "ID",
            "sortDirection": "ASC",
            "keywordSearch": "",
        }
        try:
            # We pass data=payload instead of json=payload
            body = await api._request("POST", dt_url, data=payload)
            print(f"Test 2 SUCCESS: Found {body.get('data', {}).get('totalElements') if body else 0} elements")
        except Exception as e:
            print(f"Test 2 FAILED: {e}")

        # Test 3: GET request with query parameters
        print("\n--- Test 3: GET request ---")
        dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}&pageNumber=1&pageSize=10"
        try:
            body = await api._request("GET", dt_url)
            print(f"Test 3 SUCCESS: Found {body.get('data', {}).get('totalElements') if body else 0} elements")
        except Exception as e:
            print(f"Test 3 FAILED: {e}")

        # Test 4: Different JSON keys
        print("\n--- Test 4: Different JSON keys (page instead of pageNumber, size instead of pageSize) ---")
        dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}"
        payloads = [
            {"page": 1, "size": 10},
            {"page": 0, "size": 10},
            {"pageNo": 1, "pageSize": 10},
            {"pageNumber": 1, "pageSize": 100},  # what if pageSize is too large?
            {"pageNumber": 1, "pageSize": 50},
        ]
        for idx, p in enumerate(payloads):
            try:
                body = await api._request("POST", dt_url, json=p)
                status = "SUCCESS" if body else "FAILED"
                print(f"Test 4.{idx} ({p}) {status}: {body.get('data', {}).get('totalElements') if body else 'None'}")
            except Exception as e:
                print(f"Test 4.{idx} ({p}) FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(probe())
