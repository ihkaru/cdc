"""
Repository — operasi CRUD dan upsert untuk Assignment
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import Assignment, SyncLog


class SyncStats:
    """Counter statistik per-cycle"""

    def __init__(self):
        self.total_fetched = 0
        self.total_new = 0
        self.total_updated = 0
        self.total_skipped = 0
        self.total_failed = 0
        self.total_images = 0
        self.images_mirrored = 0
        self.total_scope_metadata = 0  # Total assignments in scope (from metadata fetch)

    def __repr__(self):
        return (
            f"Fetched={self.total_fetched} | "
            f"New={self.total_new} | "
            f"Updated={self.total_updated} | "
            f"Skipped={self.total_skipped} | "
            f"Failed={self.total_failed} | "
            f"Images={self.images_mirrored}/{self.total_images}"
        )


def extract_flat_data(data: dict) -> dict:
    flat = {}
    for k, v in data.items():
        if not isinstance(v, (dict, list)):
            if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
                continue
            flat[k] = v

    pre_str = data.get("pre_defined_data")
    if pre_str and isinstance(pre_str, str) and pre_str.startswith("{"):
        try:
            for item in json.loads(pre_str).get("predata", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")
        except:
            pass

    content = data.get("content")
    if content:
        if isinstance(content, str) and content.startswith("{"):
            try:
                content = json.loads(content)
            except:
                content = {}
        if isinstance(content, dict):
            for item in content.get("data", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")

    region = data.get("region_metadata")
    if isinstance(region, dict):
        for k, v in region.items():
            if not isinstance(v, (dict, list)):
                flat[f"region_{k}"] = v
            elif k == "level" and isinstance(v, list):
                for lvl in v:
                    if isinstance(lvl, dict):
                        flat[f"region_level_{lvl.get('id')}"] = lvl.get("name")
    return flat


def normalize_bps_date(date_str: any) -> str:
    """
    Normalisasi berbagai format tanggal BPS menjadi string '20260714081317' (UTC).

    Format yang didukung:
    - int/str 13-digit unix ms : 1784016797460 → '20260714081317'
    - str 14-digit UTC compact  : '20260714081317' → '20260714081317' (passthrough)
    - BPS string WIB (2-digit hr): 'Jul 14, 2026, 03:13:17 PM' → '20260714081317'
    - BPS string WIB (1-digit hr): 'Jul 14, 2026, 3:13:17 PM'  → '20260714081317'
    """
    if not date_str:
        return ""
    s = str(date_str).strip()

    # Case 1: unix ms timestamp (13 digits)
    if s.isdigit() and len(s) == 13:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)
        return dt.strftime("%Y%m%d%H%M%S")

    # Case 2: already normalized 14-digit UTC compact string
    if s.isdigit() and len(s) == 14:
        return s

    from datetime import datetime, timedelta

    # Case 3: BPS locale string in WIB (UTC+7) — try multiple format variants
    # BPS returns both 1-digit and 2-digit hours: '3:13:17 PM' and '03:13:17 PM'
    for fmt in ("%b %d, %Y, %I:%M:%S %p", "%b %d, %Y, %I:%M:%S%p",
                "%b %-d, %Y, %I:%M:%S %p", "%b %d, %Y, %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            # BPS timestamps are WIB (UTC+7) — convert to UTC for canonical comparison
            return (dt - timedelta(hours=7)).strftime("%Y%m%d%H%M%S")
        except ValueError:
            continue

    # Case 4: Fallback — strip all non-digits and take first 14
    import re
    stripped = re.sub(r"\D", "", s)[:14]
    return stripped if len(stripped) == 14 else ""


def upsert_assignment(session: Session, data: dict, stats: SyncStats | None = None, sync_log_id: int = None) -> str:
    """
    Upsert satu assignment ke database.

    Returns:
        "new" | "updated" | "skipped"
    """
    # Hubungi ID dari berbagai kemungkinan (API detail vs API datatable)
    record_id = data.get("_id") or data.get("id") or data.get("assignment", {}).get("id")
    if not record_id:
        if stats:
            stats.total_failed += 1
        return "failed"

    # Ensure UUID object for PostgreSQL
    try:
        db_uuid = uuid.UUID(str(record_id))
    except (ValueError, TypeError):
        if stats:
            stats.total_failed += 1
        return "failed"

    # Hubungi Date Modified dari berbagai kemungkinan
    date_modified_raw = (
        data.get("date_modified")
        or data.get("dateModifiedRemote")
        or data.get("assignment", {}).get("date_modified")
        or data.get("assignment", {}).get("dateModifiedRemote")
        or ""
    )
    date_modified = normalize_bps_date(date_modified_raw)
    data_json_str = json.dumps(data, ensure_ascii=False)
    flat_data = extract_flat_data(data)

    existing = session.get(Assignment, db_uuid)

    if existing is None:
        # INSERT baru

        # Helper to safely parse UUID or return None
        def safe_uuid(val):
            if not val:
                return None
            try:
                return uuid.UUID(str(val))
            except:
                return None

        assignment = Assignment(
            id=db_uuid,
            survey_config_id=safe_uuid(data.get("_survey_config_id")),
            code_identity=(data.get("code_identity") or data.get("assignment", {}).get("codeIdentity") or ""),
            survey_period_id=safe_uuid(
                data.get("survey_period_id") or data.get("assignment", {}).get("surveyPeriodId")
            ),
            assignment_status_alias=(
                data.get("assignment_status_alias") or data.get("assignment", {}).get("assignmentStatusAlias") or ""
            ),
            current_user_username=(
                data.get("current_user_username") or data.get("assignment", {}).get("currentUserUsername") or ""
            ),
            data_json=data_json_str,
            flat_data=flat_data,
            date_modified_remote=date_modified,
            synced_to_api=False,
            sync_log_id=sync_log_id,
        )
        session.add(assignment)
        if stats:
            stats.total_new += 1
        return "new"

    elif existing.date_modified_remote != date_modified:
        # UPDATE — data berubah dari remote (status/tanggal berubah)
        existing.code_identity = (
            data.get("code_identity") or data.get("assignment", {}).get("codeIdentity") or existing.code_identity
        )
        existing.survey_period_id = (
            data.get("survey_period_id")
            or data.get("assignment", {}).get("surveyPeriodId")
            or existing.survey_period_id
        )
        existing.assignment_status_alias = (
            data.get("assignment_status_alias")
            or data.get("assignment", {}).get("assignmentStatusAlias")
            or existing.assignment_status_alias
        )
        existing.current_user_username = (
            data.get("current_user_username")
            or data.get("assignment", {}).get("currentUserUsername")
            or existing.current_user_username
        )
        existing.sync_log_id = sync_log_id
        existing.data_json = data_json_str
        existing.flat_data = flat_data
        existing.date_modified_remote = date_modified
        existing.date_synced = datetime.now(timezone.utc)
        existing.synced_to_api = False
        # Reset mirrored flag so archiver re-processes with fresh presigned URLs
        existing.local_image_mirrored = False
        existing.local_image_paths = {}
        if stats:
            stats.total_updated += 1
        return "updated"

    else:
        # SKIP — data identik
        if stats:
            stats.total_skipped += 1
        return "skipped"


def get_unsynced(session: Session, limit: int = 1000) -> list[Assignment]:
    """Ambil assignment yang belum dikirim ke API downstream."""
    return session.query(Assignment).filter(Assignment.synced_to_api == False).limit(limit).all()


def mark_synced(session: Session, ids: list[str]):
    """Tandai assignment sebagai sudah dikirim."""
    if not ids:
        return
    # Convert string IDs to UUID objects for PostgreSQL compatibility
    uuid_ids = [uuid.UUID(str(i)) for i in ids]
    session.query(Assignment).filter(Assignment.id.in_(uuid_ids)).update(
        {Assignment.synced_to_api: True}, synchronize_session="fetch"
    )
    session.commit()


def get_existing_modifications_by_ids(session: Session, ids: list[str]) -> dict[str, str]:
    """
    Ambil mapping {id: date_modified_remote} untuk list ID tertentu.
    Digunakan untuk delta check sebelum fetching detail dari API.

    Untuk dataset besar (>10k IDs), gunakan get_existing_modifications_by_ids_batched.
    """
    if not ids:
        return {}

    # Convert string IDs to UUID objects
    uuid_ids = []
    for i in ids:
        try:
            uuid_ids.append(uuid.UUID(str(i)))
        except:
            continue

    if not uuid_ids:
        return {}

    results = session.query(Assignment.id, Assignment.date_modified_remote).filter(Assignment.id.in_(uuid_ids)).all()
    return {str(r.id): r.date_modified_remote for r in results}


def get_existing_modifications_by_ids_batched(
    session: Session, ids: list[str], chunk_size: int = 10_000
) -> dict[str, str]:
    """
    Versi chunked dari get_existing_modifications_by_ids untuk dataset besar (300k+).

    Memecah list ID menjadi chunk maksimal chunk_size agar tidak membuat
    satu IN clause raksasa yang bisa timeout atau OOM di PostgreSQL.

    Returns:
        dict {assignment_id (str): date_modified_remote (str | None)}
    """
    if not ids:
        return {}

    result: dict[str, str] = {}
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        # Convert chunk to UUIDs
        uuid_chunk = []
        for cid in chunk:
            try:
                uuid_chunk.append(uuid.UUID(str(cid)))
            except:
                continue

        if not uuid_chunk:
            continue

        rows = session.query(Assignment.id, Assignment.date_modified_remote).filter(Assignment.id.in_(uuid_chunk)).all()
        result.update({str(r.id): r.date_modified_remote for r in rows})

    return result


def log_sync_run(
    session: Session,
    started_at: datetime,
    stats: SyncStats,
    notes: str = "",
    survey_config_id: str = "",
    timings: dict = None,
    total_target_remote: int = 0,
    bps_progress: list = None,
    status: str = "success",
) -> SyncLog:
    """Catat log satu cycle sinkronisasi."""
    log = SyncLog(
        survey_config_id=survey_config_id,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        total_fetched=stats.total_fetched,
        total_new=stats.total_new,
        total_updated=stats.total_updated,
        total_skipped=stats.total_skipped,
        total_failed=stats.total_failed,
        total_images=stats.total_images,
        images_mirrored=stats.images_mirrored,
        notes=notes,
        timings=timings,
        total_target_remote=total_target_remote,
        total_scope_metadata=getattr(stats, "total_scope_metadata", 0),
        bps_progress=bps_progress,
        status=status,
    )
    session.add(log)
    session.commit()
    return log


def patch_sync_log(session: Session, log_id: int, **kwargs):
    """Update fields in an existing SyncLog entry (status, counts, etc)."""
    session.query(SyncLog).filter(SyncLog.id == log_id).update(kwargs)
    session.commit()


class BatchUpserter:
    """
    Batch upsert for assignments — collects records and flushes in bulk.
    Uses ORM-level upsert (per-row) — kept for compatibility.
    For new code, prefer BatchUpserterBulk which uses SQL-level batch insert.
    """

    def __init__(self, session: Session, batch_size: int = 500):
        self.session = session
        self.batch_size = batch_size
        self._buffer: list[dict] = []
        self.stats = SyncStats()

    def add(self, data: dict):
        """Add a record to the buffer. Auto-flushes when batch_size is reached."""
        self.stats.total_fetched += 1
        record_id = data.get("_id")
        if not record_id:
            self.stats.total_failed += 1
            return

        self._buffer.append(data)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """Flush buffered records to database using batch upsert."""
        if not self._buffer:
            return

        for data in self._buffer:
            upsert_assignment(self.session, data, self.stats)

        self.session.commit()
        self._buffer.clear()

    def finish(self) -> SyncStats:
        """Flush remaining records and return final stats."""
        self.flush()
        return self.stats


class BatchUpserterBulk:
    """
    High-performance bulk upsert using PostgreSQL INSERT ... ON CONFLICT DO UPDATE.
    Sends ONE SQL statement per batch instead of N ORM calls.
    Benchmark: ~50-200x faster than per-row ORM for large datasets.
    """

    active_instance = None  # Class-level reference for signal handling

    def __init__(self, session: Session, batch_size: int = 2000, sync_log_id: int = None):
        self.session = session
        self.batch_size = batch_size
        self.sync_log_id = sync_log_id
        self._buffer: list[dict] = []
        self.stats = SyncStats()
        BatchUpserterBulk.active_instance = self

    def add(self, row: dict):
        # Transform row data for column naming to match DB
        # This part handles the mapping from API-style keys to DB-style keys
        # as pg_insert expects exact DB column names

        self.stats.total_fetched += 1
        _asgn = row.get("assignment") or {}
        date_modified_raw = (
            row.get("date_modified")
            or row.get("dateModifiedRemote")
            or _asgn.get("date_modified")        # ← key snake_case dari detail API
            or _asgn.get("dateModifiedRemote")
            or ""
        )
        date_modified = normalize_bps_date(date_modified_raw)

        db_row = {
            "id": row.get("_id") or row.get("id") or row.get("assignment", {}).get("id") or row.get("assignment", {}).get("_id"),
            "survey_config_id": row.get("_survey_config_id") or row.get("survey_config_id") or None,
            "code_identity": row.get("code_identity")
            or row.get("assignment", {}).get("code_identity")
            or row.get("assignment", {}).get("codeIdentity")
            or "",
            "survey_period_id": row.get("survey_period_id")
            or row.get("assignment", {}).get("survey_period_id")
            or row.get("assignment", {}).get("surveyPeriodId")
            or None,
            "assignment_status_alias": row.get("assignment_status_alias")
            or row.get("assignment", {}).get("assignment_status_alias")
            or row.get("assignment", {}).get("assignmentStatusAlias")
            or "",
            "current_user_username": row.get("current_user_username")
            or row.get("assignment", {}).get("current_user_username")
            or row.get("assignment", {}).get("currentUserUsername")
            or "",
            "data_json": json.dumps(row, ensure_ascii=False),
            "flat_data": extract_flat_data(row),
            "date_modified_remote": date_modified,
            "date_synced": datetime.now(timezone.utc),
            "synced_to_api": False,
            "sync_log_id": self.sync_log_id,
            "local_image_mirrored": False,
            "local_image_paths": {},
        }

        # PostgreSQL requires explicit UUID objects for bulk insert
        try:
            db_row["id"] = uuid.UUID(str(db_row["id"]))
            if db_row.get("survey_config_id"):
                db_row["survey_config_id"] = uuid.UUID(str(db_row["survey_config_id"]))
            if db_row.get("survey_period_id"):
                db_row["survey_period_id"] = uuid.UUID(str(db_row["survey_period_id"]))
        except (ValueError, TypeError) as e:
            print(f"   ⚠️ Skipping record with invalid UUID: {db_row['id']} ({e})")
            self.stats.total_failed += 1
            return

        self._buffer.append(db_row)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    async def add_async(self, row: dict):
        """Asynchronously add a row and trigger async flush if batch size is met."""
        self.stats.total_fetched += 1
        _asgn = row.get("assignment") or {}
        date_modified_raw = (
            row.get("date_modified")
            or row.get("dateModifiedRemote")
            or _asgn.get("date_modified")        # ← key snake_case dari detail API
            or _asgn.get("dateModifiedRemote")
            or ""
        )
        date_modified = normalize_bps_date(date_modified_raw)

        db_row = {
            "id": row.get("_id") or row.get("id") or row.get("assignment", {}).get("id") or row.get("assignment", {}).get("_id"),
            "survey_config_id": row.get("_survey_config_id") or row.get("survey_config_id") or None,
            "code_identity": row.get("code_identity")
            or row.get("assignment", {}).get("code_identity")
            or row.get("assignment", {}).get("codeIdentity")
            or "",
            "survey_period_id": row.get("survey_period_id")
            or row.get("assignment", {}).get("survey_period_id")
            or row.get("assignment", {}).get("surveyPeriodId")
            or None,
            "assignment_status_alias": row.get("assignment_status_alias")
            or row.get("assignment", {}).get("assignment_status_alias")
            or row.get("assignment", {}).get("assignmentStatusAlias")
            or "",
            "current_user_username": row.get("current_user_username")
            or row.get("assignment", {}).get("current_user_username")
            or row.get("assignment", {}).get("currentUserUsername")
            or "",
            "data_json": json.dumps(row, ensure_ascii=False),
            "flat_data": extract_flat_data(row),
            "date_modified_remote": date_modified,
            "date_synced": datetime.now(timezone.utc),
            "synced_to_api": False,
            "sync_log_id": self.sync_log_id,
            "local_image_mirrored": False,
            "local_image_paths": {},
        }

        # PostgreSQL requires explicit UUID objects for bulk insert
        try:
            db_row["id"] = uuid.UUID(str(db_row["id"]))
            if db_row.get("survey_config_id"):
                db_row["survey_config_id"] = uuid.UUID(str(db_row["survey_config_id"]))
            if db_row.get("survey_period_id"):
                db_row["survey_period_id"] = uuid.UUID(str(db_row["survey_period_id"]))
        except (ValueError, TypeError) as e:
            print(f"   ⚠️ Skipping record with invalid UUID: {db_row['id']} ({e})")
            self.stats.total_failed += 1
            return

        self._buffer.append(db_row)
        if len(self._buffer) >= self.batch_size:
            await self.flush_async()

    async def flush_async(self, is_emergency: bool = False):
        """Execute flush asynchronously in a background thread to prevent event loop blocking."""
        if not self._buffer:
            return
        # Create a copy of the buffer to flush so we can clear the main buffer immediately
        buffer_to_flush = self._buffer.copy()
        self._buffer.clear()
        await asyncio.to_thread(self._flush_internal, buffer_to_flush, is_emergency)

    def flush(self, is_emergency: bool = False):
        """Execute a single INSERT ... ON CONFLICT DO UPDATE for the entire batch."""
        if not self._buffer:
            return
        buffer_to_flush = self._buffer.copy()
        self._buffer.clear()
        self._flush_internal(buffer_to_flush, is_emergency)

    def _flush_internal(self, buffer: list[dict], is_emergency: bool = False):
        """Internal flush logic that actually executes the SQL."""
        if not buffer:
            return

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        prefix = "🚨 [EMERGENCY FLUSH]" if is_emergency else "💾 [BULK FLUSH]"

        try:
            stmt = pg_insert(Assignment).values(buffer)

            update_cols = {
                col: stmt.excluded[col]
                for col in [
                    "code_identity",
                    "survey_period_id",
                    "assignment_status_alias",
                    "current_user_username",
                    "data_json",
                    "flat_data",
                    "date_modified_remote",
                    "date_synced",
                    "synced_to_api",
                    "sync_log_id",
                    "local_image_mirrored",
                    "local_image_paths",
                ]
            }

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_cols,
                where=(
                    # Update jika: emergency flush, ATAU tanggal berubah, ATAU DB value masih kosong
                    # Kondisi ketiga penting untuk initial population setelah fix deploy.
                    is_emergency
                    | (Assignment.date_modified_remote != stmt.excluded.date_modified_remote)
                    | (Assignment.date_modified_remote == "")
                    | Assignment.date_modified_remote.is_(None)
                ),
            )

            result = self.session.execute(upsert_stmt)
            self.session.commit()

            inserted_or_updated = result.rowcount if result.rowcount >= 0 else len(buffer)
            skipped = len(buffer) - inserted_or_updated
            self.stats.total_new += inserted_or_updated
            self.stats.total_skipped += max(0, skipped)

            print(f"   {prefix} {len(buffer)} rows → {inserted_or_updated} upserted, {skipped} skipped")

        except Exception as e:
            print(f"   ⚠️ {prefix} failed ({e}), falling back to per-row ORM...")
            self.session.rollback()
            for row_data in buffer:
                try:
                    # Construct Assignment model directly from processed db_row dict
                    existing = self.session.get(Assignment, row_data["id"])
                    if existing is None:
                        assignment = Assignment(**row_data)
                        self.session.add(assignment)
                        self.stats.total_new += 1
                    else:
                        for k, v in row_data.items():
                            if k != "id":
                                setattr(existing, k, v)
                        self.stats.total_updated += 1
                except Exception as row_err:
                    print(f"      ❌ Fatal error on single row fallback: {row_err}")
            self.session.commit()

    def emergency_flush(self):
        """Called by signal handlers to save data before shutdown."""
        self.flush(is_emergency=True)

    def finish(self) -> SyncStats:
        """Flush remaining and return stats."""
        self.flush()
        return self.stats


def get_system_setting(session: Session, key: str) -> str | None:
    """Ambil nilai dari system_settings."""
    from .models import SystemSettings

    setting = session.get(SystemSettings, key)
    return setting.value if setting else None


def set_system_setting(session: Session, key: str, value: str):
    """Simpan atau update nilai di system_settings."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from .models import SystemSettings

    stmt = pg_insert(SystemSettings).values(key=key, value=value)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["key"], set_={"value": value, "updated_at": datetime.now(timezone.utc)}
    )
    session.execute(upsert_stmt)
    session.commit()
