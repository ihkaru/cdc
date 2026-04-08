from typing import Optional
from datetime import datetime, timezone

class SyncProgress:
    """Live progress state untuk satu sync job yang sedang berjalan."""
    phase: str = ""          # "login", "resolve", "fetch_users", "fetch_assignments", "upsert", "done"
    phase_label: str = ""    # Human-readable label yang tampil di UI
    users_total: int = 0     # Jumlah user (pencacah/pengawas) yang perlu diiterasi
    users_done: int = 0      # Berapa user yang sudah selesai diiterasi
    assignments_total: int = 0
    assignments_fetched: int = 0
    assignments_new: int = 0
    assignments_updated: int = 0
    assignments_skipped: int = 0

    def reset(self):
        self.phase = ""
        self.phase_label = ""
        self.users_total = 0
        self.users_done = 0
        self.assignments_total = 0
        self.assignments_fetched = 0
        self.assignments_new = 0
        self.assignments_updated = 0
        self.assignments_skipped = 0

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "phase_label": self.phase_label,
            "users_total": self.users_total,
            "users_done": self.users_done,
            "assignments_total": self.assignments_total,
            "assignments_fetched": self.assignments_fetched,
            "assignments_new": self.assignments_new,
            "assignments_updated": self.assignments_updated,
            "assignments_skipped": self.assignments_skipped,
        }


class SyncState:
    is_running: bool = False
    current_survey: Optional[str] = None
    current_job_id: Optional[int] = None
    last_result: Optional[dict] = None
    started_at: Optional[datetime] = None
    queue_count: int = 0
    progress: SyncProgress = SyncProgress()

sync_state = SyncState()
