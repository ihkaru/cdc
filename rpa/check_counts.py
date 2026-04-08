import asyncio
import os
import sys

# Add RPA src to path
sys.path.append("/app/src")

from api_client import FasihApiClient
from auth import fetch_vpn_cookie

async def main():
    import os
    cookie_str = os.environ.get("VPN_COOKIE")
    if not cookie_str:
        print("No VPN_COOKIE env var found")
        return
        
    # Parse a full cookie string like "a=b; c=d" into {"a": "b", "c": "d"}
    cookie = {}
    for part in cookie_str.split("; "):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookie[k] = v
            
    if not cookie:
        print("Empty cookie dict after parsing")
        return

    # Use the client as an async context manager correctly
    async with FasihApiClient(cookies=cookie) as client:
        # We found these from user's logs
        survey_id = "8712a6fc-a996-4a8f-ad6f-56a278c19288"
        period_id = "39136966-8f3c-4a0c-915b-0f65eb223475"
        
        prov_uuid, kab_uuid, reg_code, group_id = await client.get_region_metadata(
            "KALIMANTAN BARAT", "MEMPAWAH", survey_id
        )
        
        print(f"Provinsi UUID: {prov_uuid}")
        print(f"Kabupaten UUID: {kab_uuid}")
        
        url = "https://fasih-sm.bps.go.id/analytic/api/v2/assignment/report-progress-assignment"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Request report-progress for the whole province
        payload_prov = {
            "region1Id": prov_uuid,
            "region2Id": None,
            "surveyPeriodId": period_id,
            "assignmentErrorStatusType": -1,
            "filterTargetType": "TARGET_ONLY"
        }
        
        # Request report-progress for Mempawah specifically
        payload_kab = {
            "region1Id": prov_uuid,
            "region2Id": kab_uuid,
            "surveyPeriodId": period_id,
            "assignmentErrorStatusType": -1,
            "filterTargetType": "TARGET_ONLY"
        }
        
        # Use client.session for the actual request
        async with client.session.post(url, json=payload_prov, headers=headers) as resp:
            print(f"Provinsi Status: {resp.status}")
            print("Provinsi Result:", await resp.text())
            
        async with client.session.post(url, json=payload_kab, headers=headers) as resp:
            print(f"Kabupaten Status: {resp.status}")
            print("Kabupaten Result:", await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
