import asyncio
import os
import aiohttp
import ssl
from dotenv import load_dotenv

load_dotenv()
TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
COOKIE = os.getenv("VPN_COOKIE", "")

async def main():
    period_id = "a4f9069c-752a-44c7-ae6c-f58f1721aed4"
    prov_uuid = "2e656c4f-02e2-4272-890b-9e6e555867f1"
    kab_uuid = "6cb109bb-46ab-4fec-8f01-b6e0205d151b"
    
    url = f"{TARGET_URL}/analytic/api/v2/assignment/datatable-all-user-survey-periode"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Cookie": COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"{TARGET_URL}/survey-collection/collect/83f6053d-2120-4e7a-b322-d350bb975dd0",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    payload = {
        "draw": 1,
        "columns": [
            {"data": "id", "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
            {"data": "codeIdentity", "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}},
            {"data": "data1", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data2", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data3", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data4", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data5", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data6", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data7", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data8", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data9", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}},
            {"data": "data10", "name": "", "searchable": True, "orderable": True, "search": {"value": "", "regex": False}}
        ],
        "order": [{"column": 0, "dir": "asc"}],
        "start": 0,
        "length": 1000,
        "search": {"value": "", "regex": False},
        "assignmentExtraParam": {
            "region1Id": kab_uuid,           
            "region2Id": None,
            "region3Id": None,
            "region4Id": None,
            "region5Id": None,
            "region6Id": None,
            "region7Id": None,
            "region8Id": None,
            "region9Id": None,
            "region10Id": None,
            "surveyPeriodId": period_id,
            "assignmentErrorStatusType": -1,
            "assignmentStatusAlias": None,
            "data1": None,
            "data2": None,
            "data3": None,
            "data4": None,
            "data5": None,
            "data6": None,
            "data7": None,
            "data8": None,
            "data9": None,
            "data10": None,
            "userIdResponsibility": None,
            "currentUserId": None,
            "regionId": None,
            "filterTargetType": "TARGET_ONLY"
        }
    }
    
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(ssl=ssl_ctx)) as session:
        payload["assignmentExtraParam"]["region1Id"] = prov_uuid
        payload["assignmentExtraParam"]["region2Id"] = kab_uuid
        print("--- TEST: Prov di Region 1, Kab di Region 2 ---")
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            print("totalHit:", data.get("totalHit"))
            print("SearchData len:", len(data.get("searchData", [])))

if __name__ == "__main__":
    asyncio.run(main())
