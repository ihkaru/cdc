"""
Repository — operasi CRUD dan upsert untuk Assignment
"""
import json
from datetime import datetime, timezone
from typing import Optional

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

    def __repr__(self):
        return (
            f"Fetched={self.total_fetched} | "
            f"New={self.total_new} | "
            f"Updated={self.total_updated} | "
            f"Skipped={self.total_skipped} | "
            f"Failed={self.total_failed}"
        )


def extract_flat_data(data: dict) -> dict:
    flat = {}
    for k, v in data.items():
        if not isinstance(v, (dict, list)):
            if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                continue
            flat[k] = v
            
    pre_str = data.get("pre_defined_data")
    if pre_str and isinstance(pre_str, str) and pre_str.startswith('{'):
        try:
            for item in json.loads(pre_str).get("predata", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")
        except:
            pass
            
    content = data.get("content")
    if content:
        if isinstance(content, str) and content.startswith('{'):
            try: content = json.loads(content)
            except: content = {}
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


def upsert_assignment(session: Session, data: dict, stats: Optional[SyncStats] = None) -> str:
    """
    Upsert satu assignment ke database.
    
    Returns:
        "new" | "updated" | "skipped"
    """
    record_id = data.get("_id")
    if not record_id:
        if stats:
            stats.total_failed += 1
        return "failed"

    date_modified = data.get("date_modified", "")
    data_json_str = json.dumps(data, ensure_ascii=False)
    flat_data = extract_flat_data(data)

    existing = session.get(Assignment, record_id)

    if existing is None:
        # INSERT baru
        assignment = Assignment(
            id=record_id,
            survey_config_id=data.get("_survey_config_id", ""),
            code_identity=data.get("code_identity", ""),
            survey_period_id=data.get("survey_period_id", ""),
            assignment_status_alias=data.get("assignment_status_alias", ""),
            current_user_username=data.get("current_user_username", ""),
            data_json=data_json_str,
            flat_data=flat_data,
            date_modified_remote=date_modified,
            synced_to_api=False,
        )
        session.add(assignment)
        if stats:
            stats.total_new += 1
        return "new"

    elif existing.date_modified_remote != date_modified:
        # UPDATE — data berubah
        existing.code_identity = data.get("code_identity", existing.code_identity)
        existing.survey_period_id = data.get("survey_period_id", existing.survey_period_id)
        existing.assignment_status_alias = data.get("assignment_status_alias", existing.assignment_status_alias)
        existing.current_user_username = data.get("current_user_username", existing.current_user_username)
        existing.data_json = data_json_str
        existing.flat_data = flat_data
        existing.date_modified_remote = date_modified
        existing.date_synced = datetime.now(timezone.utc)
        existing.synced_to_api = False  # Perlu dikirim ulang
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
    return (
        session.query(Assignment)
        .filter(Assignment.synced_to_api == False)
        .limit(limit)
        .all()
    )


def mark_synced(session: Session, ids: list[str]):
    """Tandai assignment sebagai sudah dikirim."""
    session.query(Assignment).filter(Assignment.id.in_(ids)).update(
        {Assignment.synced_to_api: True}, synchronize_session="fetch"
    )
    session.commit()


def get_existing_modifications_by_ids(session: Session, ids: list[str]) -> dict[str, str]:
    """
    Ambil mapping {id: date_modified_remote} untuk list ID tertentu.
    Digunakan untuk mengecek apakah data di DB sudah up-to-date sebelum fetching dari API.
    """
    if not ids:
        return {}
    
    results = (
        session.query(Assignment.id, Assignment.date_modified_remote)
        .filter(Assignment.id.in_(ids))
        .all()
    )
    return {r.id: r.date_modified_remote for r in results}


def log_sync_run(
    session: Session,
    started_at: datetime,
    stats: SyncStats,
    notes: str = "",
    survey_config_id: str = "",
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
        notes=notes,
    )
    session.add(log)
    session.commit()
    return log


class BatchUpserter:
    """
    Batch upsert for assignments — collects records and flushes in bulk.
    Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for efficient bulk operations.
    At 5M+ rows, per-row commits are ~500x slower than batch commits.
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

