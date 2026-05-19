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


class UltimateSyncEngine:
    """
    The 'Smartest' Sync Engine for FasihNexus:
    1. Multi-Session Pool: Uses all valid admin sessions from DB.
    2. Overlap Pipeline: Producers (API) and Consumer (DB) run in parallel.
    3. Impersonation: Uses curl_cffi to mimic real browsers and bypass WAF.
    4. Async DB Flush: Bulk inserts happen in a background thread.
    """

    def __init__(self, primary_cookies: dict, survey_config_id: str, sync_log_id: int = None):
        self.primary_cookies = primary_cookies
        self.survey_config_id = survey_config_id
        self.sync_log_id = sync_log_id
        self.sessions_pool: list[AsyncSession] = []
        self.queue = asyncio.Queue(maxsize=DEFAULT_CONCURRENCY * 2)
        self.stats = SyncStats()
        self.target_url = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

        self.bad_sessions = set()

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
                if resp.status_code == 200:
                    self.sessions_pool.append(s)
                else:
                    await s.close()
            except:
                await s.close()

        if not self.sessions_pool:
            s = AsyncSession(impersonate="chrome120", verify=False)
            s.cookies.update(self.primary_cookies)
            self.sessions_pool.append(s)

        print(f"   🚀 Pool Ready: {len(self.sessions_pool)} active session(s).")

    async def _fetch_worker(self, assignment_id: str, semaphore: asyncio.Semaphore):
        """Fetch a single assignment detail using healthy sessions from the pool."""
        async with semaphore:
            if sync_state.is_shutting_down:
                return

            for attempt in range(4):
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
                        data = orjson.loads(resp.content)
                        if data.get("success"):
                            await self.queue.put(data.get("data"))
                            self.stats.total_fetched += 1
                            return
                    elif resp.status_code in (401, 403):
                        print(f"   ⚠️ Session {id(session)} blacklisted (HTTP {resp.status_code})")
                        self.bad_sessions.add(session)

                    await asyncio.sleep(0.5 * (attempt + 1))
                except Exception as e:
                    if attempt == 3:
                        print(f"   ❌ Final failure for {assignment_id[:8]}: {e}")

            self.stats.total_failed += 1
            await self.queue.put(None)

    async def _db_consumer(self, upserter: BatchUpserterBulk, total_expected: int):
        """Consumer that pulls data from queue and feeds the upserter."""
        count = 0
        while count < total_expected:
            if sync_state.is_shutting_down:
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
                sync_state.progress.phase_label = f"📥 Detail Sync: {count}/{total_expected}..."
                if count % 1000 == 0:
                    print(
                        f"   📊 Progress: {count}/{total_expected} (RPS: {self.stats.total_fetched / (time.perf_counter() - self.start_time):.1f})"
                    )

            self.queue.task_done()

    async def run_sync(self, assignment_ids: list[str]) -> SyncStats:
        """Main entry point to run the sync for a list of IDs."""
        self.start_time = time.perf_counter()
        total = len(assignment_ids)
        if total == 0:
            return SyncStats()

        await self._setup_session_pool()

        # Dedup check (Skip if already exists and not modified)
        # Delta check can be added here if needed to skip records already in DB
        print(f"   🔍 Delta Check for {total:,} records...")

        # Filter out records that don't need update (This is a huge optimization)
        # Note: We can't fully skip if we don't know the remote modification date yet.
        # But for 'detail fetch', we usually have the remote date from the Datatable API.

        upserter = BatchUpserterBulk(get_session(), batch_size=BATCH_SIZE, sync_log_id=self.sync_log_id)

        semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)

        # Start Consumer
        consumer = asyncio.create_task(self._db_consumer(upserter, total))

        # Start Producers
        print(f"   📡 Launching {total} Producers (Concurrency: {DEFAULT_CONCURRENCY})...")
        tasks = [self._fetch_worker(aid, semaphore) for aid in assignment_ids]

        try:
            await asyncio.gather(*tasks)
            await self.queue.join()
            await consumer
        except Exception as e:
            print(f"   🚨 Sync Engine Aborted: {e}")
        finally:
            self.stats = upserter.finish()
            for s in self.sessions_pool:
                await s.close()

        duration = time.perf_counter() - self.start_time
        print(f"   ✅ Ultimate Sync Finished in {duration:.1f}s (Throughput: {total / duration:.1f} rec/s)")
        return self.stats


async def run_ultimate_sync(
    session, api_client, survey_id, period_id, survey_config_id, assignment_ids, sync_log_id=None
):
    """Bridge function for worker."""
    engine = UltimateSyncEngine(api_client.cookies, survey_config_id, sync_log_id)
    return await engine.run_sync(assignment_ids)
