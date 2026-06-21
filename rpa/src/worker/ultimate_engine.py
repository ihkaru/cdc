import asyncio
import json
import os
import random
import time

import orjson
from curl_cffi.requests import AsyncSession

from db.connection import get_session
from db.models import SystemSettings
from db.repository import BatchUpserterBulk, SyncStats
from state import sync_state

# Tuning parameters
DEFAULT_CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "50"))
BATCH_SIZE = 2000
RETRY_DELAY = 0.3  # flat delay in seconds (not exponential)
MAX_RELOGIN_ATTEMPTS = 3


class UltimateSyncEngine:
    """
    The 'Smartest' Sync Engine for FasihNexus:
    1. Multi-Session Pool: Uses all valid admin sessions from DB.
    2. Overlap Pipeline: Producers (API) and Consumer (DB) run in parallel.
    3. Impersonation: Uses curl_cffi to mimic real browsers and bypass WAF.
    4. Async DB Flush: Bulk inserts happen in a background thread.
    """

    def __init__(
        self,
        primary_cookies: dict,
        survey_config_id: str,
        sync_log_id: int = None,
        sso_username: str = "",
        sso_password: str = "",
    ):
        self.primary_cookies = primary_cookies
        self.survey_config_id = survey_config_id
        self.sync_log_id = sync_log_id
        self.sso_username = sso_username
        self.sso_password = sso_password
        self.sessions_pool: list[AsyncSession] = []
        self.queue = asyncio.Queue(maxsize=DEFAULT_CONCURRENCY * 2)
        self.stats = SyncStats()
        self.target_url = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
        self.bad_sessions = set()
        self._total_assignments = 0  # set at run time for progress reporting

    async def _setup_session_pool(self):
        """Initialize multiple sessions from DB sso_state_* entries."""
        print("   👥 Initializing Multi-Session Pool...")

        all_cookie_dicts = [self.primary_cookies]

        # Load from DB
        session_db = get_session()
        records = session_db.query(SystemSettings).filter(SystemSettings.key.like("sso_state_%")).all()
        for rec in records:
            try:
                c_data = json.loads(rec.value)
                cookies = c_data.get("cookies") if isinstance(c_data, dict) and "cookies" in c_data else c_data
                if isinstance(cookies, list):
                    cookies = {c["name"]: c["value"] for c in cookies}

                if (
                    cookies
                    and "SESSION" in cookies
                    and not any(s.get("SESSION") == cookies["SESSION"] for s in all_cookie_dicts)
                ):
                    all_cookie_dicts.append(cookies)
            except:
                continue
        session_db.close()

        # Validate and create curl_cffi sessions
        for c_dict in all_cookie_dicts:
            s = AsyncSession(impersonate="chrome120", verify=False)
            s.cookies.update(c_dict)
            try:
                resp = await s.get(f"{self.target_url}/survey/api/v1/users/myinfo", timeout=5)
                # BPS Fortinet returns HTTP 200 with HTML body (login redirect) on expired sessions.
                # Must check content to confirm it's a real JSON API response, not an SSO page.
                content_type = resp.headers.get("content-type", "")
                body_text = resp.text[:500] if hasattr(resp, "text") else ""
                is_html_response = (
                    "text/html" in content_type
                    or body_text.lstrip().startswith("<!")
                    or ("login" in body_text.lower() and "<html" in body_text.lower())
                )
                if resp.status_code == 200 and not is_html_response:
                    self.sessions_pool.append(s)
                    print("   ✅ Session validated (JSON response, HTTP 200).")
                else:
                    reason = "HTML redirect" if is_html_response else f"HTTP {resp.status_code}"
                    print(f"   ⚠️ Session rejected: {reason} — SSO cookie likely expired.")
                    await s.close()
            except Exception as e:
                print(f"   ⚠️ Session validation failed: {e}")
                await s.close()

        if not self.sessions_pool:
            print("   🚨 No valid sessions found! Forcing primary cookies (may fail if also expired).")
            s = AsyncSession(impersonate="chrome120", verify=False)
            s.cookies.update(self.primary_cookies)
            self.sessions_pool.append(s)

        print(f"   🚀 Pool Ready: {len(self.sessions_pool)} active session(s).")

    async def _fetch_worker(self, assignment_id: str, semaphore: asyncio.Semaphore):
        """Fetch a single assignment detail using healthy sessions from the pool."""
        if sync_state.stop_requested or sync_state.is_shutting_down:
            await self.queue.put(None)
            return

        async with semaphore:
            if sync_state.stop_requested or sync_state.is_shutting_down:
                await self.queue.put(None)
                return

            for attempt in range(4):
                if sync_state.stop_requested or sync_state.is_shutting_down:
                    await self.queue.put(None)
                    return
                # Filter out bad sessions
                healthy_pool = [s for s in self.sessions_pool if s not in self.bad_sessions]
                if not healthy_pool:
                    # If all sessions are bad, try primary as last resort
                    healthy_pool = self.sessions_pool[:1]

                session = random.choice(healthy_pool)
                url = f"{self.target_url}/app/api/assignment-general/api/assignment/get-by-assignment-id?assignmentId={assignment_id}"

                try:
                    resp = await session.get(url, timeout=25)
                    if resp.status_code == 200:
                        # Guard: BPS returns HTTP 200 with HTML body on expired sessions.
                        content_type = resp.headers.get("content-type", "")
                        if "text/html" in content_type or resp.content[:50].lstrip().startswith(b"<!"):
                            print(
                                f"   🚨 [{assignment_id[:8]}] Session returned HTML (login redirect). "
                                f"Blacklisting session and retrying..."
                            )
                            self.bad_sessions.add(session)
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue

                        try:
                            data = orjson.loads(resp.content)
                        except Exception as parse_err:
                            print(
                                f"   ❌ [{assignment_id[:8]}] JSON parse failed: {parse_err}. Body: {resp.text[:100]}"
                            )
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue

                        if data.get("success"):
                            await self.queue.put(data.get("data"))
                            self.stats.total_fetched += 1
                            return
                        else:
                            print(f"   ⚠️ [{assignment_id[:8]}] API success=False. Body: {str(data)[:100]}")
                    elif resp.status_code in (401, 403):
                        print(f"   ⚠️ Session {id(session)} blacklisted (HTTP {resp.status_code})")
                        self.bad_sessions.add(session)

                    await asyncio.sleep(0.5 * (attempt + 1))
                except Exception as e:
                    if attempt == 3:
                        print(f"   ❌ Final failure for {assignment_id[:8]}: {type(e).__name__}: {e!r}")
                    await asyncio.sleep(RETRY_DELAY)

            self.stats.total_failed += 1
            await self.queue.put(None)

    async def _db_consumer(self, upserter: BatchUpserterBulk, total_expected: int):
        """Consumer that pulls data from queue and feeds the upserter."""
        count = 0
        while count < total_expected:
            if sync_state.stop_requested or sync_state.is_shutting_down:
                break

            data = await self.queue.get()
            count += 1
            if data:
                upserter.add(
                    {
                        "_id": data.get("id"),
                        "assignment": data,
                        "responses": [],
                        "_survey_config_id": self.survey_config_id,
                    }
                )

            if count % 100 == 0 or count == total_expected:
                elapsed = time.perf_counter() - self.start_time
                rps = count / elapsed if elapsed > 0 else 0
                sync_state.progress.assignments_fetched = count
                sync_state.progress.phase_label = f"⬇️ Detail Sync: {count}/{total_expected} — {rps:.1f} rec/s"
                if count % 1000 == 0:
                    print(f"   📊 Progress: {count}/{total_expected} (RPS: {rps:.1f})")

            self.queue.task_done()

    async def run_sync(self, assignment_ids: list[str]) -> SyncStats:
        """Main entry point to run the sync for a list of IDs."""
        self.start_time = time.perf_counter()
        total = len(assignment_ids)
        self._total_assignments = total
        if total == 0:
            return SyncStats()

        await self._setup_session_pool()

        print(f"   🔍 Delta Check for {total:,} records...")

        upserter = BatchUpserterBulk(get_session(), batch_size=BATCH_SIZE, sync_log_id=self.sync_log_id)

        # ---------------------------------------------------------------
        # Resilient Pipeline with Re-login support
        # ---------------------------------------------------------------
        semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)
        remaining_ids = list(assignment_ids)
        relogin_attempts = 0

        while remaining_ids:
            if sync_state.stop_requested or sync_state.is_shutting_down:
                print("   🛑 Stop signal detected in run_sync. Exiting loop...")
                break

            total_this_batch = len(remaining_ids)
            consumer = asyncio.create_task(self._db_consumer(upserter, total_this_batch))

            print(
                f"   📡 Launching {total_this_batch:,} Producers "
                f"(Concurrency: {DEFAULT_CONCURRENCY}, Sessions: {len(self.sessions_pool)})..."
            )

            auth_error_detected = False
            failed_at_id: str | None = None

            async def _run_workers(ids: list[str]):
                nonlocal auth_error_detected, failed_at_id
                tasks = [self._fetch_worker(aid, semaphore) for aid in ids]
                try:
                    await asyncio.gather(*tasks)
                except Exception as exc:
                    print(f"   ⚠️ Worker gather error: {type(exc).__name__}: {exc!r}")

            await _run_workers(remaining_ids)
            await self.queue.join()
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass

            # Detect if all sessions went bad (auth expired across all workers)
            healthy_sessions = [s for s in self.sessions_pool if s not in self.bad_sessions]
            all_sessions_dead = len(healthy_sessions) == 0

            if not all_sessions_dead:
                # Normal completion — no resilient re-login needed
                break

            # All sessions dead → try resilient re-login
            if not self.sso_username or not self.sso_password:
                print(
                    "   ❌ All sessions died but no credentials for re-login. "
                    f"Stats so far: {self.stats.total_fetched} fetched, {self.stats.total_failed} failed."
                )
                break

            relogin_attempts += 1
            if relogin_attempts > MAX_RELOGIN_ATTEMPTS:
                print(f"   ❌ Max re-login attempts ({MAX_RELOGIN_ATTEMPTS}) reached. Stopping.")
                break

            print(
                f"   🔄 [Resilient] All sessions expired. Re-login attempt {relogin_attempts}/{MAX_RELOGIN_ATTEMPTS}..."
            )
            new_cookies = await self._relogin_headless()
            if not new_cookies:
                print("   ❌ Headless re-login failed. Stopping.")
                break

            # Close old dead sessions and rebuild pool
            for s in self.sessions_pool:
                try:
                    await s.close()
                except Exception:
                    pass
            self.sessions_pool.clear()
            self.bad_sessions.clear()

            new_s = AsyncSession(impersonate="chrome120", verify=False)
            new_s.cookies.update(new_cookies)
            self.sessions_pool.append(new_s)
            self.primary_cookies = new_cookies
            print("   ✅ [Resilient] Session baru aktif. Melanjutkan sync...")

            # Find which IDs still haven't been successfully fetched
            remaining_ids = [aid for aid in remaining_ids if self.stats.total_fetched < total]
            if not remaining_ids:
                break

        try:
            self.stats = upserter.finish()
        except Exception:
            pass
        finally:
            for s in self.sessions_pool:
                try:
                    await s.close()
                except Exception:
                    pass

        duration = time.perf_counter() - self.start_time
        rps = total / duration if duration > 0 else 0
        print(
            f"   ✅ Ultimate Sync Finished in {duration:.1f}s "
            f"(Throughput: {rps:.1f} rec/s, Fetched: {self.stats.total_fetched}, Failed: {self.stats.total_failed})"
        )
        return self.stats

    async def _relogin_headless(self) -> dict | None:
        """Perform headless Playwright re-login and return fresh cookie dict."""
        try:
            from playwright.async_api import async_playwright

            from auth import auto_login, launch_stealth_browser, new_stealth_context

            print("   🔄 [ReLogin] Session expired. Memulai headless re-login via Playwright...")
            async with async_playwright() as p:
                browser = await launch_stealth_browser(p)
                context = await new_stealth_context(browser)
                try:
                    page = await context.new_page()
                    ok, new_cookies, err = await auto_login(page, self.sso_username, self.sso_password)
                    if ok and new_cookies:
                        print(f"   ✅ [ReLogin] Re-login berhasil ({len(new_cookies)} cookies).")
                        return new_cookies
                    else:
                        print(f"   ❌ [ReLogin] Re-login gagal: {err}")
                        return None
                finally:
                    await browser.close()
        except Exception as e:
            print(f"   ❌ [ReLogin] Exception: {type(e).__name__}: {e!r}")
            return None


async def run_ultimate_sync(
    session,
    api_client,
    survey_id,
    period_id,
    survey_config_id,
    assignment_ids,
    sync_log_id=None,
    sso_username: str = "",
    sso_password: str = "",
):
    """Bridge function for worker."""
    engine = UltimateSyncEngine(
        api_client.cookies,
        survey_config_id,
        sync_log_id,
        sso_username=sso_username,
        sso_password=sso_password,
    )
    return await engine.run_sync(assignment_ids)
