import asyncio
import os
import re
import ssl
from functools import wraps

import aiohttp

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")


class FasihAuthError(Exception):
    """Exception raised when SSO session is expired or redirected to login page."""


def with_retry(retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except FasihAuthError:
                    raise
                except Exception as e:
                    last_err = e
                    print(f"   ⚠️ [API] Attempt {attempt}/{retries} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            print(f"   ❌ [API] Failed after {retries} attempts.")
            raise last_err

        return wrapper

    return decorator


class FasihApiClient:
    def __init__(self, cookies: dict[str, str]):
        self.cookies = cookies
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

        # Use a persistent cookie jar and session
        self.jar = aiohttp.CookieJar(unsafe=True)
        self._session: aiohttp.ClientSession | None = None

        # Pre-populate jar with initial cookies from Playwright
        from yarl import URL

        target_url = URL(TARGET_URL)
        for name, value in self.cookies.items():
            self.jar.update_cookies({name: value}, target_url)

    async def __aenter__(self):
        """Open a single persistent ClientSession for the entire sync cycle."""
        # Initial headers bootstrap
        headers = self._get_headers()

        self._session = aiohttp.ClientSession(
            cookie_jar=self.jar,
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100, limit_per_host=30),
            timeout=aiohttp.ClientTimeout(total=45, connect=15),
        )

        # Optional: Bootstrap hit to ensure session and F5 cookies are active
        try:
            async with self._session.get(f"{TARGET_URL}/") as resp:
                if resp.status == 200:
                    print("   🌐 [API] Session bootstrapped successfully (HTTP 200)")
                else:
                    print(f"   ⚠️ [API] Session bootstrap returned status {resp.status}")
        except Exception as e:
            print(f"   ⚠️ [API] Session bootstrap failed: {e}")

        # Log active cookies sample for debugging (masked for security)
        try:
            sample = []
            for c in self.jar:
                val = c.value[:4] + "..." if len(c.value) > 4 else "***"
                sample.append(f"{c.key}={val}")
            print(f"   🐛 [API] Active Cookies: {', '.join(sample)}")
        except:
            pass

        return self

    async def _request(self, method: str, path: str, **kwargs) -> dict | None:
        """Perform a request using the persistent ClientSession, with Response Guardian redirect checks."""
        url = f"{TARGET_URL}/{path.lstrip('/')}"

        # Merge dynamic headers
        req_headers = self._get_headers()
        if "headers" in kwargs:
            req_headers.update(kwargs.pop("headers"))

        try:
            async with self.session.request(method, url, headers=req_headers, **kwargs) as resp:
                # 1. Response Guardian: Detect SSO Login redirects (Scenario 2)
                if "oauth_login" in str(resp.url) or "sso.bps.go.id" in str(resp.url):
                    print(
                        "   🚨 [API] Response Guardian: Detected redirection to SSO login. Session expired!", flush=True
                    )
                    raise FasihAuthError("Session expired: redirected to SSO login")

                # 2. Check for explicit authentication statuses
                if resp.status in (401, 403):
                    print(f"   🚨 [API] Authentication failed (HTTP {resp.status})", flush=True)
                    raise FasihAuthError(f"Authentication failed with HTTP {resp.status}")

                if resp.status != 200:
                    text = await resp.text()
                    print(f"   ⚠️ [API] Request to {path} failed (HTTP {resp.status}): {text[:200]}", flush=True)
                    return None

                # Try to parse json
                try:
                    return await resp.json()
                except Exception as json_err:
                    text = await resp.text()
                    # If it's HTML, check if it's the SSO login page (in case redirect wasn't fully detected by URL)
                    if "<html" in text.lower() and ("login" in text.lower() or "sso" in text.lower()):
                        print(
                            "   🚨 [API] Response Guardian: Detected HTML login page structure. Session expired!",
                            flush=True,
                        )
                        raise FasihAuthError("Session expired: returned HTML login page instead of JSON")
                    print(f"   ⚠️ [API] Failed to parse JSON response from {path}: {json_err}", flush=True)
                    return None
        except FasihAuthError:
            raise
        except Exception as e:
            print(f"   ⚠️ [API] Connection error during request to {path}: {e}", flush=True)
            raise

    def _get_headers(self) -> dict[str, str]:
        """Dynamically build headers with latest XSRF-TOKEN from cookie jar."""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest",
        }

        # Try to find XSRF-TOKEN in the cookie jar
        xsrf_token = None
        for cookie in self.jar:
            if cookie.key == "XSRF-TOKEN":
                from urllib.parse import unquote

                raw_token = cookie.value
                xsrf_token = unquote(raw_token)
                if raw_token != xsrf_token:
                    print(f"   🐛 [API] Header XSRF-TOKEN unquoted: {raw_token[:5]}... -> {xsrf_token[:5]}...")
                break

        if xsrf_token:
            headers["X-XSRF-TOKEN"] = xsrf_token

        return headers

    async def close(self):
        await self.__aexit__()

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(
                cookie_jar=self.jar,
                headers=self._get_headers(),
                connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100, limit_per_host=30),
                timeout=aiohttp.ClientTimeout(total=45, connect=15),
            )
        return self._session

    # Keep backward-compat for old code that calls create_session()
    async def create_session(self) -> aiohttp.ClientSession:
        """Deprecated: returns self._session if open, otherwise creates a temp one."""
        if self._session and not self._session.closed:

            class _Noop:
                """Fake async context manager wrapping existing session."""

                def __init__(self, s):
                    self._s = s

                async def __aenter__(self):
                    return self._s

                async def __aexit__(self, *a):
                    pass

            return _Noop(self._session)  # type: ignore
        # Fallback for any call outside context manager
        return aiohttp.ClientSession(
            cookie_jar=self.jar,
            headers=self._get_headers(),
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100),
            timeout=aiohttp.ClientTimeout(total=45, connect=15),
        )

    @with_retry()
    async def get_survey_id(self, survey_name: str) -> str | None:
        """Cari Survey ID berdasarkan nama survey"""
        print(f"📋 [API] Mencari survey: '{survey_name}'...")

        path = "survey/api/v1/surveys/datatable?surveyType=Pencacahan"
        target_clean = re.sub(r"[^a-z0-9]", "", survey_name.lower())

        all_surveys = []
        page = 0
        while True:
            payload = {
                "pageNumber": page,
                "pageSize": 100,
                "sortBy": "CREATED_AT",
                "sortDirection": "DESC",
                "keywordSearch": "",
            }

            body = await self._request("POST", path, json=payload)
            if not body or not body.get("success"):
                break

            data = body.get("data", {}).get("content", [])
            if not data:
                break

            all_surveys.extend(data)

            total_pages = body.get("data", {}).get("totalPage", 1)
            if page >= total_pages - 1:
                break

            page += 1

        # Exact Match (normalized alphanumeric and lowercase)
        for survey in all_surveys:
            s_name = survey.get("name", "")
            s_clean = re.sub(r"[^a-z0-9]", "", s_name.lower())
            if target_clean == s_clean:
                s_id = survey.get("id")
                print(f"   ✅ [API] Ditemukan (Exact Match): '{s_name}' → ID: {s_id}")
                return s_id

        print(f"   ❌ [API] Survey '{survey_name}' tidak ditemukan dari seluruh halaman (Exact Match required).")
        return None

    @with_retry()
    async def get_survey_period_and_roles(self, survey_id: str) -> tuple[str | None, list[str], str | None]:
        """Mendapatkan Active Period ID, semua Role ID, dan surveyRoleGroupId untuk suatu survey."""
        print(f"   📋 [API] Mencari periode survey dan role untuk ID: {survey_id}...")

        path = f"survey/api/v1/survey-periods?surveyId={survey_id}"
        body = await self._request("GET", path)
        if not body:
            return None, [], None

        periods = body.get("data", [])
        if not periods:
            print("   ❌ [API] Tidak ada periode ditemukan.")
            return None, [], None

        period_id = periods[0].get("id")

        # Also check /my endpoint
        my_body = await self._request("GET", f"survey/api/v1/survey-periods/my?surveyId={survey_id}")
        if my_body and my_body.get("data"):
            period_id = my_body["data"][0].get("id")
            print(f"   📅 [API] Menggunakan period dari /my: {period_id}")

        # Fetch role ID + role group ID
        role_body = await self._request("GET", f"survey/api/v1/survey-roles?surveyId={survey_id}")
        if not role_body:
            return period_id, [], None

        roles = role_body.get("data", [])
        role_ids = [r.get("id") for r in roles] if roles else []
        role_group_id = roles[0].get("surveyRoleGroupId") if roles else None

        print(f"   ✅ [API] Period: {period_id}, {len(role_ids)} roles, group: {role_group_id}")
        return period_id, role_ids, role_group_id

    @with_retry()
    async def get_analytic_assignment_count(
        self, period_id: str, region1_id: str | None = None, region2_id: str | None = None
    ) -> int:
        """Mendapatkan total assignments yang ditargetkan di remote FASIH-SM."""
        print(f"   📊 [API] Menghitung total target assignment di remote (Period: {period_id[:8]}...)...")
        path = "analytic/api/v2/assignment/report-progress-assignment"
        payload = {
            "region1Id": region1_id,
            "region2Id": region2_id,
            "surveyPeriodId": period_id,
            "assignmentStatusAlias": None,
            "assignmentErrorStatusType": -1,
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
            "currentUserId": None,
            "userIdResponsibility": None,
            "filterTargetType": "TARGET_ONLY",
        }
        body = await self._request("POST", path, json=payload)
        try:
            if body and isinstance(body, list) and len(body) > 0:
                values = body[0].get("values", [])
                for val in values:
                    if val.get("label") == "total":
                        count = int(val.get("value", 0))
                        print(f"   ✅ [API] Remote Target Count: {count}")
                        return count
        except Exception as e:
            print(f"   ⚠️ [API] Gagal mengurai jumlah analytic count: {e}")
        return 0
        return None, [], None

    @with_retry()
    async def get_region_metadata(
        self, provinsi_name: str | None, kabupaten_name: str | None, survey_id: str
    ) -> tuple[str | None, str | None, str | None, str]:
        """Mencari UUID region berdasarkan teks filter UI."""
        print("   🔍 [API] Menarik struktur metadata region...")

        # Get Region Group ID
        group_id = "82af087a-d063-48b9-8633-71c84c4e7422"  # Standard fallback
        s_data = await self._request("GET", f"survey/api/v1/surveys/{survey_id}")
        if s_data and s_data.get("data"):
            fetched_group = s_data["data"].get("regionGroupId")
            if fetched_group:
                group_id = fetched_group
                print(f"   ✅ [API] Extracted dynamic regionGroupId: {group_id}")

        # Get Provincial Region Code
        prov_uuid, prov_full_code = None, None
        if provinsi_name:
            data = await self._request("GET", f"region/api/v1/region/level1?groupId={group_id}")
            if data:
                regions = data.get("data", [])
                clean_prov_name = re.sub(r"\[\d+\]", "", provinsi_name).lower().strip()
                search_words = [w for w in clean_prov_name.split(" ") if len(w) > 2]
                for r in regions:
                    label = r.get("name", "").lower()
                    if all(word in label for word in search_words):
                        prov_uuid = r.get("id")
                        prov_full_code = r.get("fullCode")
                        break

        # Get Kabupaten Region UUID
        kab_uuid, kab_full_code = None, None
        if kabupaten_name and prov_full_code:
            data = await self._request(
                "GET", f"region/api/v1/region/level2?groupId={group_id}&level1FullCode={prov_full_code}"
            )
            if data:
                regions = data.get("data", [])
                clean_kab_name = re.sub(r"\[\d+\]", "", kabupaten_name).lower().strip()
                search_words = [w for w in clean_kab_name.split(" ") if len(w) > 2]
                for r in regions:
                    label = r.get("name", "").lower()
                    if all(word in label for word in search_words):
                        kab_uuid = r.get("id")
                        kab_full_code = r.get("fullCode")
                        break

        region_uuid_for_filter = kab_uuid if kab_uuid else prov_uuid
        region_full_code = kab_full_code if kab_full_code else prov_full_code
        return prov_uuid, region_uuid_for_filter, region_full_code, group_id

    @with_retry()
    async def get_sub_regions(self, level: int, group_id: str, parent_full_code: str) -> list[dict]:
        """Menarik daftar sub-wilayah (Kecamatan/Desa) untuk level 3 atau 4."""
        parent_level = level - 1
        url = f"region/api/v1/region/level{level}?groupId={group_id}&level{parent_level}FullCode={parent_full_code}"
        data = await self._request("GET", url)
        if data and isinstance(data, dict):
            return data.get("data", [])
        return []

    @with_retry()
    async def get_users_by_region(
        self, period_id: str, role_ids: list[str], region_code: str, role_group_id: str | None = None
    ) -> tuple[list[dict], list[dict]]:
        """Mendapatkan pengawas & pencacah."""
        pengawas_list = []
        pencacah_list = []
        seen_ids: set = set()

        def _add_user(user: dict, is_pencacah: bool):
            uid = user.get("userId") or user.get("id")
            if not uid or uid in seen_ids:
                return
            seen_ids.add(uid)
            entry = {
                "fullname": user.get("fullname", "") or user.get("user", {}).get("fullname", ""),
                "username": user.get("username", "") or user.get("user", {}).get("username", ""),
                "userId": uid,
                "isPencacah": is_pencacah,
                "description": user.get("description", ""),
            }
            if is_pencacah:
                pencacah_list.append(entry)
            else:
                pengawas_list.append(entry)

        for role_id in role_ids:
            path = f"survey/api/v1/survey-period-role-users/region?surveyPeriodId={period_id}&surveyRoleId={role_id}&regionCode={region_code}"
            body = await self._request("GET", path)
            if body and body.get("data"):
                for user in body["data"]:
                    _add_user(user, user.get("isPencacah", False))

        if role_group_id:
            for role_id in role_ids:
                dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}"
                payload = {
                    "pageNumber": 0,
                    "pageSize": 200,
                    "sortBy": "ID",
                    "sortDirection": "ASC",
                    "keywordSearch": "",
                }
                body = await self._request("POST", dt_url, json=payload)
                if body and body.get("data"):
                    for user in body["data"].get("searchData", []):
                        role_info = user.get("surveyRole", {})
                        is_pencacah = role_info.get("isPencacah", False)
                        flat = {
                            "userId": user.get("userId"),
                            "fullname": user.get("user", {}).get("fullname", ""),
                            "username": user.get("user", {}).get("username", ""),
                            "description": role_info.get("description", ""),
                            "isPencacah": is_pencacah,
                        }
                        _add_user(flat, is_pencacah)

        return pengawas_list, pencacah_list

    @with_retry()
    async def get_assignments_metadata(
        self,
        period_id: str,
        prov_uuid: str | None = None,
        kab_uuid: str | None = None,
        kec_uuid: str | None = None,
        desa_uuid: str | None = None,
        pengawas_id: str | None = None,
        pencacah_id: str | None = None,
        region_group_id: str | None = None,
    ) -> list[dict]:
        """Tarik Assignment Datatable secara paralel."""
        path = "analytic/api/v2/assignment/datatable-all-user-survey-periode"
        # Tune page size to avoid BPS 504 Gateway Time-out on large datasets (e.g. Sensus Ekonomi)
        page_size = int(os.getenv("FASIH_PAGE_SIZE", "200"))

        def _build_payload(start):
            p = {
                "draw": (start // page_size) + 1,
                "columns": [
                    {"data": "id", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}}
                ],
                "order": [{"column": 0, "dir": "asc"}],
                "start": start,
                "length": page_size,
                "search": {"value": "", "regex": False},
                "assignmentExtraParam": {
                    "region1Id": prov_uuid,
                    "region2Id": kab_uuid,
                    "region3Id": kec_uuid,
                    "region4Id": desa_uuid,
                    "surveyPeriodId": period_id,
                    "assignmentErrorStatusType": -1,
                    "filterTargetType": os.getenv("FASIH_FILTER_TARGET_TYPE", "TARGET_ONLY"),
                    "regionGroupId": region_group_id,
                },
            }
            if pencacah_id or pengawas_id:
                p["assignmentExtraParam"]["currentUserId"] = pencacah_id or pengawas_id
            return p

        # 1. Fetch first page to get total
        print("   📋 [API] Fetching metadata page 0...")
        first_body = await self._request("POST", path, json=_build_payload(0))
        if not first_body:
            return []

        total_records = (
            first_body.get("recordsTotal", 0) or first_body.get("recordsFiltered", 0) or first_body.get("totalHit", 0)
        )
        print(f"   📊 Total records to metadata-sync: {total_records}")

        all_metadata = []

        def _parse_data(body):
            data_list = []
            search_data = body.get("data", body.get("searchData", []))
            for item in search_data:
                rec_id = item.get("id") or item.get("_id") or item.get("assignmentId")
                remote_date_raw = (
                    item.get("dateModified")
                    or item.get("updatedAt")
                    or item.get("dateModifiedRemote")
                    or item.get("date_modified")
                )
                if rec_id:
                    data_list.append({"id": rec_id, "dateModifiedRemote": self._norm_date(remote_date_raw)})
            return data_list

        all_metadata.extend(_parse_data(first_body))

        if total_records <= page_size:
            return all_metadata

        # 2. Fetch remaining pages in parallel
        offsets = range(page_size, total_records, page_size)
        print(f"   📡 Launching {len(offsets)} parallel metadata requests...")

        async def _fetch_page(offset):
            body = await self._request("POST", path, json=_build_payload(offset))
            return _parse_data(body) if body else []

        results = await asyncio.gather(*(_fetch_page(o) for o in offsets))
        for res in results:
            all_metadata.extend(res)

        return all_metadata

    def _norm_date(self, d_raw):
        if not d_raw:
            return ""
        s = str(d_raw).strip()
        if s.isdigit() and len(s) == 14:
            return s
        from datetime import datetime, timedelta

        try:
            dt = datetime.strptime(s, "%b %d, %Y, %I:%M:%S %p")
            return (dt - timedelta(hours=7)).strftime("%Y%m%d%H%M%S")
        except:
            return re.sub(r"\D", "", s)[:14]

    @with_retry(retries=3, delay=2)
    async def get_assignment_detail(self, assignment_id: str) -> dict | None:
        """Fetch the latest assignment detail JSON (includes fresh S3 links)."""
        # Correct path: /app/api/assignment-general/api/assignment/get-by-assignment-id
        # Note: ultimate_engine.py builds its own URL — this method is used by archiver/other callers.
        url = (
            f"{TARGET_URL}/app/api/assignment-general/api/assignment/get-by-assignment-id?assignmentId={assignment_id}"
        )
        print(f"   🔄 [API] Refreshing detail for assignment: {assignment_id}...")

        async with await self.create_session() as session:
            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"   ❌ [API] Failed to fetch detail (HTTP {resp.status}): {text[:200]}")
                    return None

                # Guard: BPS Fortinet returns HTTP 200 with HTML login page when session is expired.
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    text = await resp.text()
                    if "login" in text.lower() or "sso" in text.lower():
                        print("   🚨 [API] get_assignment_detail: Received HTML login page (session expired)!")
                        raise FasihAuthError("Session expired: returned HTML login page on assignment detail fetch")
                    print("   ⚠️ [API] get_assignment_detail: Received unexpected HTML response.")
                    return None

                try:
                    body = await resp.json(content_type=None)
                except Exception as json_err:
                    text = await resp.text()
                    print(f"   ❌ [API] JSON parse failed for detail: {json_err}. Body[:200]: {text[:200]}")
                    return None

                if body and body.get("success"):
                    data = body.get("data")
                    if data:
                        # Log data keys to trace structure
                        keys = list(data.keys()) if isinstance(data, dict) else "list"
                        print(f"   ✨ [API] Detail fetch success. Top-level keys: {keys}")
                    return data

                print(f"   ❌ [API] Detail fetch failed success=False. Body: {body}")
                return None

    @with_retry(retries=3, delay=2)
    async def get_fresh_image_urls(self, survey_period_id: str, assignments_payload: list[dict]) -> dict:
        """
        Request new S3 presigned URLs for expired images.
        Payload structure matching BPS backend:
        [{"assignmentId": "...", "fileNames": ["filename.jpg", ...]}]
        """
        try:
            url = f"{TARGET_URL}/assignment-general/api/image/presigned-url-get?surveyPeriodId={survey_period_id}"

            # Sanitize payload: Ensure fileNames only contain the simplified identifier (basename),
            # stripping any surveyPeriodId/ or other path prefixes to avoid 400 Bad Request errors.
            sanitized_payload = []
            for item in assignments_payload:
                clean_filenames = []
                for fn in item.get("fileNames", []):
                    clean_fn = fn.split("/")[-1].split("?")[0]
                    clean_filenames.append(clean_fn)
                sanitized_payload.append({"assignmentId": item.get("assignmentId"), "fileNames": clean_filenames})

            print(
                f"   🔄 [API] Requesting {sum(len(a.get('fileNames', [])) for a in sanitized_payload)} fresh presigned URLs...",
                flush=True,
            )

            headers = self._get_headers()
            print(f"   🐛 [API] X-XSRF-TOKEN in header: {headers.get('X-XSRF-TOKEN', 'MISSING')[:10]}...", flush=True)

            async with await self.create_session() as session:
                async with session.post(url, json=sanitized_payload, headers=headers, timeout=45) as resp:
                    status = resp.status
                    print(f"   🐛 [API] POST /presigned-url-get returned status {status}", flush=True)

                    if status != 200:
                        text = await resp.text()
                        print(f"   ❌ [API] Failed to fetch fresh presigned URLs (HTTP {status})", flush=True)
                        print(f"   🐛 [API] Request URL: {url}", flush=True)
                        print(f"   🐛 [API] Error Body: {text[:500]}", flush=True)
                        return None

                    raw_data = await resp.json()
                    print(f"   🐛 [API] raw_data received: {str(raw_data)[:100]}...", flush=True)

                    # Unwrap BPS API standard response { "success": true, "data": ... }
                    if isinstance(raw_data, dict) and "success" in raw_data and "data" in raw_data:
                        actual_data = raw_data.get("data", [])
                    else:
                        actual_data = raw_data

                    result_map = {}
                    if isinstance(actual_data, list):
                        for item in actual_data:
                            if isinstance(item, dict):
                                urls_list = item.get("presignedUrls", [])
                                for url_obj in urls_list:
                                    if (
                                        isinstance(url_obj, dict)
                                        and "fileName" in url_obj
                                        and "presignedUrl" in url_obj
                                    ):
                                        result_map[url_obj["fileName"]] = url_obj["presignedUrl"]
                    elif isinstance(actual_data, dict):
                        result_map = actual_data

                    print(f"   🐛 [API] Found {len(result_map)} urls in result_map", flush=True)
                    return result_map
        except Exception as e:
            print(f"   ❌ [API] Error fetching presigned URLs: {e}", flush=True)
            import traceback

            traceback.print_exc()
            return None

    @with_retry(retries=3, delay=2)
    async def download_content(self, url: str) -> bytes | None:
        """Download raw content from a URL using the authenticated session, forcing cookies for cross-domain S3."""
        if not self._session:
            return None

        # Manually extract cookies from jar to bypass domain restrictions in aiohttp
        cookie_header = ""
        try:
            cookies = []
            for cookie in self.jar:
                cookies.append(f"{cookie.key}={cookie.value}")
            cookie_header = "; ".join(cookies)
        except:
            pass

        headers = self._get_headers()
        if cookie_header:
            headers["Cookie"] = cookie_header

        async with self._session.get(url, headers=headers, timeout=60) as resp:
            if resp.status == 200:
                return await resp.read()

            print(f"   ❌ [API] Content download failed (HTTP {resp.status}): {url[:100]}...")
            return None
