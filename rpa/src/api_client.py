import os
import aiohttp
import ssl
import re
from typing import List, Dict, Tuple, Optional

import asyncio
from functools import wraps

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

def with_retry(retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    print(f"   ⚠️ [API] Attempt {attempt}/{retries} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            print(f"   ❌ [API] Failed after {retries} attempts.")
            raise last_err
        return wrapper
    return decorator

class FasihApiClient:
    def __init__(self, cookies: Dict[str, str]):
        self.cookies = cookies
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.jar = aiohttp.CookieJar(unsafe=True)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Open a single persistent ClientSession for the entire sync cycle."""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{TARGET_URL}/",
            "Origin": TARGET_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        if "XSRF-TOKEN" in self.cookies:
            headers["X-XSRF-TOKEN"] = self.cookies["XSRF-TOKEN"]

        self._session = aiohttp.ClientSession(
            cookies=self.cookies,
            cookie_jar=self.jar,
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100, limit_per_host=30),
            timeout=aiohttp.ClientTimeout(total=45, connect=15)
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("FasihApiClient must be used as an async context manager: async with FasihApiClient(cookies) as api:")
        return self._session

    # Keep backward-compat for old code that calls create_session()
    async def create_session(self) -> aiohttp.ClientSession:
        """Deprecated: returns self._session if open, otherwise creates a temp one."""
        if self._session and not self._session.closed:
            class _Noop:
                """Fake async context manager wrapping existing session."""
                def __init__(self, s): self._s = s
                async def __aenter__(self): return self._s
                async def __aexit__(self, *a): pass
            return _Noop(self._session)  # type: ignore
        # Fallback for any call outside context manager
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{TARGET_URL}/",
            "Origin": TARGET_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        if "XSRF-TOKEN" in self.cookies:
            headers["X-XSRF-TOKEN"] = self.cookies["XSRF-TOKEN"]
        return aiohttp.ClientSession(
            cookies=self.cookies,
            cookie_jar=self.jar,
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100),
            timeout=aiohttp.ClientTimeout(total=45, connect=15)
        )

    @with_retry(retries=3, delay=5)
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

    @with_retry(retries=3, delay=5)
    async def get_survey_period_and_roles(self, survey_id: str) -> Tuple[Optional[str], List[str], Optional[str]]:
        """Mendapatkan Active Period ID, semua Role ID, dan surveyRoleGroupId untuk suatu survey."""
        print(f"   📋 [API] Mencari periode survey dan role untuk ID: {survey_id}...")
        
        async with await self.create_session() as session:
            url = f"{TARGET_URL}/survey/api/v1/survey-periods?surveyId={survey_id}"
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    print(f"   ❌ [API] Gagal (HTTP {resp.status})")
                    return None, [], None
                    
                body = await resp.json()
                periods = body.get("data", [])
                
                if not periods:
                    print(f"   ❌ [API] Tidak ada periode ditemukan.")
                    return None, [], None
                    
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
                
                # Fetch role ID + role group ID
                role_url = f"{TARGET_URL}/survey/api/v1/survey-roles?surveyId={survey_id}"
                async with session.get(role_url, headers={"Accept": "application/json"}) as role_resp:
                    role_body = await role_resp.json()
                    roles = role_body.get("data", [])
                    role_ids = [r.get("id") for r in roles] if roles else []
                    # surveyRoleGroupId is shared across all roles for a survey
                    role_group_id = roles[0].get("surveyRoleGroupId") if roles else None
                    
                print(f"   ✅ [API] Period: {period_id}, {len(role_ids)} roles, group: {role_group_id}")
                return period_id, role_ids, role_group_id
        return None, [], None

    @with_retry(retries=3, delay=5)
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

    @with_retry(retries=3, delay=5)
    async def get_kecamatans(self, group_id: str, kab_full_code: str) -> List[Dict]:
        """Dapatkan list kecamatan (level 3) dalam suatu kabupaten."""
        url = f"{TARGET_URL}/region/api/v1/region/level3?groupId={group_id}&level2FullCode={kab_full_code}"
        print(f"   🔍 [API] Menarik list kecamatan untuk Kab {kab_full_code}...")
        async with await self.create_session() as session:
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"   ❌ [API] Gagal fetch kecamatan (HTTP {resp.status}): {text}")
                    return []
                data = await resp.json()
                kec_list = data.get("data", [])
                print(f"   ✅ [API] Ditemukan {len(kec_list)} kecamatan.")
                return kec_list

    @with_retry(retries=3, delay=5)
    async def get_users_by_region(
        self, period_id: str, role_ids: List[str],
        region_code: str, role_group_id: Optional[str] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Mendapatkan pengawas & pencacah via:
        1. Endpoint /region (pencacah — pakai full region code)
        2. Endpoint /datatable (admin/pengawas — tidak pakai region filter,
           karena admin kabupaten sering punya regionId 4-digit bukan 8-digit
           sehingga tidak muncul di endpoint /region)
        """
        pengawas_list = []  # semua non-pencacah (pengawas + admin)
        pencacah_list = []
        seen_ids: set = set()

        def _add_user(user: dict, is_pencacah: bool):
            uid = user.get('userId') or user.get('id')
            if not uid or uid in seen_ids:
                return
            seen_ids.add(uid)
            entry = {
                'fullname': user.get('fullname', '') or user.get('user', {}).get('fullname', ''),
                'username': user.get('username', '') or user.get('user', {}).get('username', ''),
                'userId': uid,
                'isPencacah': is_pencacah,
                'description': user.get('description', ''),
            }
            if is_pencacah:
                pencacah_list.append(entry)
            else:
                pengawas_list.append(entry)

        async with await self.create_session() as session:
            # --- 1. Region endpoint: baik untuk pencacah & pengawas lokal ---
            for role_id in role_ids:
                url = (
                    f"{TARGET_URL}/survey/api/v1/survey-period-role-users/region"
                    f"?surveyPeriodId={period_id}&surveyRoleId={role_id}&regionCode={region_code}"
                )
                async with session.get(url, headers={"Accept": "application/json"}) as resp:
                    if resp.status != 200:
                        continue
                    body = await resp.json()
                    for user in body.get("data", []):
                        _add_user(user, user.get('isPencacah', False))

            # --- 2. Datatable endpoint: untuk admin yang tidak muncul di /region ---
            # Admin kabupaten sering punya regionId 4-digit (mis: "6104") bukan full code
            # sehingga endpoint /region tidak mengembalikannya
            if role_group_id:
                for role_id in role_ids:
                    dt_url = (
                        f"{TARGET_URL}/analytic/api/v2/survey-period-role-user/datatable"
                        f"?surveyPeriodId={period_id}"
                        f"&surveyRoleGroupId={role_group_id}"
                        f"&surveyRoleId={role_id}"
                    )
                    payload = {"pageNumber": 0, "pageSize": 200, "sortBy": "ID", "sortDirection": "ASC", "keywordSearch": ""}
                    async with session.post(dt_url, json=payload, headers={"Accept": "application/json"}) as resp:
                        if resp.status != 200:
                            continue
                        body = await resp.json()
                        for user in body.get("data", {}).get("searchData", []):
                            role_info = user.get("surveyRole", {})
                            is_pencacah = role_info.get("isPencacah", False)
                            # Flatten: userId dari user.user.id, fullname dari user.user.fullname
                            flat = {
                                'userId': user.get("userId"),
                                'fullname': user.get("user", {}).get("fullname", ""),
                                'username': user.get("user", {}).get("username", ""),
                                'description': role_info.get("description", ""),
                                'isPencacah': is_pencacah,
                            }
                            _add_user(flat, is_pencacah)

        print(
            f"   📋 [API] Extracted: {len(pengawas_list)} non-pencacah (pengawas/admin), "
            f"{len(pencacah_list)} pencacah"
        )
        for u in pengawas_list:
            print(f"      👤 {u['description'] or 'non-pencacah'}: {u['fullname']} ({u['userId'][:8]}...)")
        return pengawas_list, pencacah_list

    @with_retry(retries=3, delay=5)
    async def get_assignments_metadata(self, period_id: str, prov_uuid: Optional[str] = None, kab_uuid: Optional[str] = None, 
                                       kec_uuid: Optional[str] = None,
                                       pengawas_id: Optional[str] = None, pencacah_id: Optional[str] = None, region_group_id: Optional[str] = None) -> List[Dict]:
        """Tarik Assignment Datatable hingga habis per filter combo.
        Menggunakan format assignmentExtraParam yang sesuai dengan payload UI Angular."""
        url = f"{TARGET_URL}/analytic/api/v2/assignment/datatable-all-user-survey-periode"
        all_metadata = []
        page_start = 0
        page_size = 1000
        while True:
            # Build payload
            payload = {
                "draw": (page_start // page_size) + 1,
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
                    "region3Id": kec_uuid,
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
                    "currentUserId": pencacah_id or pengawas_id or "",
                    "regionId": None,
                    "filterTargetType": None,
                    "regionGroupId": region_group_id
                }
            }

            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"   ❌ [API] Datatable pagination gagal at start={page_start} (HTTP {resp.status}): {text[:500]}")
                    break
                    
                body = await resp.json()
                if page_start == 0:
                    total_hit = body.get('totalHit', body.get('recordsTotal', 0))
                    print(f"   📊 [API] Total records in server: {total_hit}")

                search_data = body.get("data", body.get("searchData", []))
                if not search_data:
                    break

                for item in search_data:
                    all_metadata.append({
                        "id": item.get("id"),
                        "dateModifiedRemote": item.get("dateModified"),
                        "code_identity": item.get("codeIdentity")
                    })

                # Update progress label
                try:
                    from state import sync_state as _ss
                    _ss.progress.phase_label = (
                        f"🌏 Fetching assignments: {len(all_metadata)} records fetched..."
                    )
                except Exception:
                    pass

                print(f"   📄 [API] Slice fetch start={page_start}: {len(search_data)} records (total: {len(all_metadata)})")

                if len(search_data) < page_size:
                    break
                page_start += page_size

        return all_metadata
