import os
import aiohttp
import ssl
import re
from typing import List, Dict, Tuple, Optional

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

class FasihApiClient:
    def __init__(self, cookies: Dict[str, str]):
        self.cookies = cookies
        # Matatkan SSL check karena VPN internal bisa jadi self-signed/bermasalah
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        
        self.jar = aiohttp.CookieJar(unsafe=True)
        # Load the cookies we got from Playwright into the jar. 
        # aiohttp parses cookies per domain so we don't strictly *need* the jar 
        # but providing it along with raw `cookies` to the session helps with redirects
        
    async def create_session(self) -> aiohttp.ClientSession:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{TARGET_URL}/",
            "Origin": TARGET_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        
        # Angular default CSRF protection
        if "XSRF-TOKEN" in self.cookies:
            headers["X-XSRF-TOKEN"] = self.cookies["XSRF-TOKEN"]
            
        return aiohttp.ClientSession(
            cookies=self.cookies,
            cookie_jar=self.jar,
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=50)
        )

    async def get_survey_id(self, survey_name: str) -> Optional[str]:
        """Cari Survey ID berdasarkan nama survey"""
        print(f"📋 [API] Mencari survey: '{survey_name}'...")
        
        url = f"{TARGET_URL}/survey/api/v1/surveys/datatable?surveyType=Pencacahan"
        target_clean = re.sub(r'[^a-z0-9]', '', survey_name.lower())
        
        async with await self.create_session() as session:
            page = 0
            while True:
                payload = {
                    "pageNumber": page,
                    "pageSize": 100,
                    "sortBy": "CREATED_AT",
                    "sortDirection": "DESC",
                    "keywordSearch": ""
                }
                
                async with session.post(url, json=payload, headers={"Accept": "application/json"}) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"   ❌ [API] Gagal fetch survey list (HTTP {resp.status}): {text}")
                        return None
                        
                    body = await resp.json()
                    if not body or not body.get("success"):
                        print("   ❌ [API] Survey root list failed success=False")
                        return None
                        
                    data = body.get("data", {}).get("content", [])
                    if not data:
                        break
                        
                    for survey in data:
                        s_name = survey.get("name", "")
                        s_clean = re.sub(r'[^a-z0-9]', '', s_name.lower())
                        if target_clean and (target_clean in s_clean or s_clean in target_clean):
                            s_id = survey.get("id")
                            print(f"   ✅ [API] Ditemukan: '{s_name}' → ID: {s_id}")
                            return s_id
                            
                    total_pages = body.get("data", {}).get("totalPage", 1)
                    if page >= total_pages - 1:
                        break
                    
                    page += 1
                        
            print(f"   ❌ [API] Survey '{survey_name}' tidak ditemukan dari seluruh halaman.")
            return None

    async def get_survey_period_and_roles(self, survey_id: str) -> Tuple[Optional[str], List[str]]:
        """Mendapatkan Active Period ID dan semua Role ID untuk suatu survey."""
        print(f"   📋 [API] Mencari periode survey dan role untuk ID: {survey_id}...")
        
        async with await self.create_session() as session:
            url = f"{TARGET_URL}/survey/api/v1/survey-periods?surveyId={survey_id}"
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    print(f"   ❌ [API] Gagal (HTTP {resp.status})")
                    return None, []
                    
                body = await resp.json()
                periods = body.get("data", [])
                
                if not periods:
                    print(f"   ❌ [API] Tidak ada periode ditemukan.")
                    return None, []
                    
                print(f"   📅 [API] {len(periods)} periode tersedia:")
                for i, p in enumerate(periods):
                    print(f"      [{i}] ID: {p.get('id')} | Name: {p.get('name')} | Status: {p.get('status') or p.get('statusSurveyPeriod')}")
                    
                period_id = periods[0].get("id")
                
                # Also check /my endpoint to see if user has a different active period
                my_period_url = f"{TARGET_URL}/survey/api/v1/survey-periods/my?surveyId={survey_id}"
                async with session.get(my_period_url, headers={"Accept": "application/json"}) as my_resp:
                    if my_resp.status == 200:
                        my_body = await my_resp.json()
                        my_periods = my_body.get("data", [])
                        if my_periods:
                            period_id = my_periods[0].get("id")
                            print(f"   📅 [API] Menggunakan period dari /my: {period_id}")
                
                # Fetch role ID
                role_url = f"{TARGET_URL}/survey/api/v1/survey-roles?surveyId={survey_id}"
                async with session.get(role_url, headers={"Accept": "application/json"}) as role_resp:
                    role_body = await role_resp.json()
                    roles = role_body.get("data", [])
                    role_ids = [r.get("id") for r in roles] if roles else []
                    
                print(f"   ✅ [API] Validasi Period ID: {period_id}, {len(role_ids)} Role ID ditemukan")
                return period_id, role_ids
        return None, []

    async def get_region_metadata(self, provinsi_name: Optional[str], kabupaten_name: Optional[str], survey_id: str) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
        """Mencari UUID region berdasarkan teks filter UI (misal: '[61] KALIMANTAN BARAT').
        Returns (prov_uuid, kab_uuid_or_prov_uuid, region_full_code, region_group_id)."""
        print("   🔍 [API] Menarik struktur metadata region...")
        
        async with await self.create_session() as session:
            # Get Region Group ID
            group_id = "82af087a-d063-48b9-8633-71c84c4e7422"  # Standard fallback
            try:
                survey_url = f"{TARGET_URL}/survey/api/v1/surveys/{survey_id}"
                async with session.get(survey_url, headers={"Accept": "application/json"}) as resp:
                    if resp.status == 200:
                        s_data = await resp.json()
                        fetched_group = s_data.get("data", {}).get("regionGroupId")
                        if fetched_group:
                            group_id = fetched_group
                            print(f"   ✅ [API] Extracted dynamic regionGroupId: {group_id}")
            except Exception as e:
                print(f"   ⚠️ [API] Failed fetching dynamic regionGroupId, using fallback: {e}")
        async with await self.create_session() as session:
            # Get Provincial Region Code (UUID + fullCode)
            prov_uuid, prov_full_code = None, None
            if provinsi_name:
                prov_url = f"{TARGET_URL}/region/api/v1/region/level1?groupId={group_id}"
                async with session.get(prov_url, headers={"Accept": "application/json"}) as resp:
                    data = await resp.json()
                    regions = data.get("data", [])
                    
                    clean_prov_name = re.sub(r'\[\d+\]', '', provinsi_name).lower().strip()
                    search_words = [w for w in clean_prov_name.split(' ') if w]
                    print(f"   🔍 [API] Mencari Provinsi: {search_words} di {len(regions)} regions...")
                    
                    for r in regions:
                        label = r.get("name", "").lower()
                        if all(word in label for word in search_words):
                            prov_uuid = r.get("id")
                            prov_full_code = r.get("fullCode")
                            print(f"   ✅ [API] Match Provinsi: {r.get('name')} → UUID: {prov_uuid}, Code: {prov_full_code}")
                            break
                            
            # Get Kabupaten Region UUID
            kab_uuid = None
            
            if kabupaten_name and prov_full_code:
                kab_url = f"{TARGET_URL}/region/api/v1/region/level2?groupId={group_id}&level1FullCode={prov_full_code}"
                async with session.get(kab_url, headers={"Accept": "application/json"}) as resp:
                    data = await resp.json()
                    regions = data.get("data", [])
                    
                    clean_kab_name = re.sub(r'\[\d+\]', '', kabupaten_name).lower().strip()
                    search_words = [w for w in clean_kab_name.split(' ') if w]
                    print(f"   🔍 [API] Mencari Kabupaten: {search_words} di {len(regions)} regions...")
                    
                    for r in regions:
                        label = r.get("name", "").lower()
                        if all(word in label for word in search_words):
                            kab_uuid = r.get("id")
                            kab_full_code = r.get("fullCode")
                            print(f"   ✅ [API] Match Kabupaten: {r.get('name')} → UUID: {kab_uuid}, Code: {kab_full_code}")
                            break
            
            # Return (prov_uuid, region_uuid_for_filter, region_full_code)
            # region_uuid_for_filter = kabupaten UUID jika ada, else provinsi UUID
            # region_full_code = kabupaten code jika ada, else provinsi code
            region_uuid_for_filter = kab_uuid if kab_uuid else prov_uuid
            region_full_code = kab_full_code if kab_full_code else prov_full_code
            
            return prov_uuid, region_uuid_for_filter, region_full_code, group_id
            
        return None, None, None, group_id

    async def get_users_by_region(self, period_id: str, role_ids: List[str], region_code: str) -> Tuple[List[Dict], List[Dict]]:
        """Mendapatkan pengawas & pencacah dengan iterasi API `survey-period-role-users/region` berdasarkan multiple roles"""
        
        pengawas_list = []
        pencacah_list = []
        
        async with await self.create_session() as session:
            for role_id in role_ids:
                url = f"{TARGET_URL}/survey/api/v1/survey-period-role-users/region?surveyPeriodId={period_id}&surveyRoleId={role_id}&regionCode={region_code}"
                async with session.get(url, headers={"Accept": "application/json"}) as resp:
                    if resp.status != 200:
                        continue
                        
                    body = await resp.json()
                    users = body.get("data", [])
                    
                    for user in users:
                        entry = {
                            'fullname': user.get('fullname', ''),
                            'username': user.get('username', ''),
                            'userId': user.get('userId', ''),
                            'isPencacah': user.get('isPencacah', False),
                            'description': user.get('description', ''),
                        }
                        # Cegah duplikasi jika satu user merangkap multiple role? Kita tampung saja, filter di UI
                        if user.get('isPencacah'):
                            # Prevent exact duplicates
                            if not any(u['userId'] == entry['userId'] for u in pencacah_list):
                                pencacah_list.append(entry)
                        else:
                            if not any(u['userId'] == entry['userId'] for u in pengawas_list):
                                pengawas_list.append(entry)
                                
        print(f"   📋 [API] Extracted: {len(pengawas_list)} pengawas, {len(pencacah_list)} pencacah")
        return pengawas_list, pencacah_list

    async def get_assignments_metadata(self, period_id: str, prov_uuid: Optional[str] = None, kab_uuid: Optional[str] = None, 
                                       pengawas_id: Optional[str] = None, pencacah_id: Optional[str] = None, region_group_id: Optional[str] = None) -> List[Dict]:
        """Tarik Assignment Datatable hingga habis per filter combo.
        Menggunakan format assignmentExtraParam yang sesuai dengan payload UI Angular."""
        url = f"{TARGET_URL}/analytic/api/v2/assignment/datatable-all-user-survey-periode"
        
        all_metadata = []
        page_start = 0
        page_size = 1000
        
        async with await self.create_session() as session:
            while True:
                # Payload menyerupai persis yang dikirim UI Angular FASIH-SM
                # region1Id = Provinsi, region2Id = Kabupaten
                payload = {
                    "draw": page_start // page_size + 1,
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
                    "start": page_start,
                    "length": page_size,
                    "search": {"value": "", "regex": False},
                    "assignmentExtraParam": {
                        "region1Id": prov_uuid,
                        "region2Id": kab_uuid,
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
                        "currentUserId": pengawas_id or pencacah_id,
                        "regionId": None,
                        "filterTargetType": "TARGET_ONLY",
                        "regionGroupId": region_group_id
                    }
                }
                
                async with session.post(url, json=payload, headers={"Accept": "application/json"}) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"   ❌ [API] Datatable pagination gagal at start={page_start} (HTTP {resp.status}): {text[:500]}")
                        break
                        
                    body = await resp.json()
                    
                    # Debug: print response keys on first page
                    if page_start == 0:
                        print(f"   [DEBUG] Response keys: {list(body.keys())}")
                        print(f"   [DEBUG] totalHit: {body.get('totalHit', 'N/A')}")
                        sd = body.get("searchData", [])
                        print(f"   [DEBUG] searchData size: {len(sd)}")
                        if sd:
                            print(f"   [DEBUG] First record keys: {list(sd[0].keys())}")
                    
                    search_data = body.get("data", body.get("searchData", []))
                    
                    if not search_data:
                        break  # no more data
                        
                    for item in search_data:
                        all_metadata.append({
                            "id": item.get("id"),
                            "dateModifiedRemote": item.get("dateModified"),
                            "code_identity": item.get("codeIdentity")
                        })
                    
                    print(f"   📄 [API] Page start={page_start}: {len(search_data)} records")
                        
                    # Jika dapat kurang dari page_size, berarti sudah habis
                    if len(search_data) < page_size:
                        break
                        
                    page_start += page_size
                    
        return all_metadata
