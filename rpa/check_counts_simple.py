import asyncio
import aiohttp
import os
import json

async def main():
    cookie_str = os.environ.get("VPN_COOKIE")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": cookie_str
    }
    
    period_id = "39136966-8f3c-4a0c-915b-0f65eb223475"
    url = "https://fasih-sm.bps.go.id/analytic/api/v2/assignment/report-progress-assignment"
    
    # Payload matching user's snippet exactly (with None for null)
    payload = {
        "region1Id": None,
        "region2Id": None,
        "surveyPeriodId": period_id,
        "assignmentErrorStatusType": -1,
        "filterTargetType": "TARGET_ONLY"
    }
    
    # Mempawah specific IDs from previous successful run
    prov_uuid = "7b66fe41-2039-4bb0-aa49-53a0fe5a5a4f"
    kab_uuid = "f38718fd-1994-44c8-bd29-2b6ac4c1b492"
    
    payload_kab = {
        "region1Id": prov_uuid,
        "region2Id": kab_uuid,
        "surveyPeriodId": period_id,
        "assignmentErrorStatusType": -1,
        "filterTargetType": "TARGET_ONLY"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print("--- Testing FULL (Province Level Rollup) ---")
        async with session.post(url, json=payload) as resp:
            print(f"Status: {resp.status}")
            print("Result:", await resp.text())
            
        print("\n--- Testing MEMPAWAH ONLY ---")
        async with session.post(url, json=payload_kab) as resp:
            print(f"Status: {resp.status}")
            print("Result:", await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
