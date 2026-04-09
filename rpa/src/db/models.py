"""
Database models — SQLAlchemy ORM (PostgreSQL + SQLite compatible)
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class SurveyConfig(Base):
    """Config satu survey — credentials, filter, interval."""
    __tablename__ = "survey_configs"

    id = Column(String, primary_key=True, comment="UUID")
    survey_name = Column(String, nullable=False, comment="Nama survey di FASIH")
    sso_username = Column(String, nullable=False)
    sso_password_encrypted = Column(String, nullable=False, comment="AES-encrypted")
    filter_provinsi = Column(String, default="")
    filter_kabupaten = Column(String, default="")
    filter_rotation = Column(String, default="pengawas")
    interval_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SurveyConfig(name={self.survey_name}, active={self.is_active})>"


class Assignment(Base):
    """Setiap baris = 1 assignment dari FASIH-SM"""
    __tablename__ = "assignments"

    id = Column(String, primary_key=True, comment="UUID _id dari API FASIH")
    survey_config_id = Column(String, ForeignKey("survey_configs.id", ondelete="CASCADE"),
                              index=True, comment="FK ke survey_configs")
    code_identity = Column(String, index=True, comment="Kode identitas")
    survey_period_id = Column(String, comment="UUID periode survey")
    assignment_status_alias = Column(String, comment="Status: OPEN, SUBMITTED, dll")
    current_user_username = Column(String, comment="Username pencacah/pengawas")
    data_json = Column(JSON, comment="Full JSON payload dari API")
    flat_data = Column(JSON, default={}, comment="Flattened metric columns")
    date_modified_remote = Column(String, comment="date_modified dari API")
    sync_log_id = Column(Integer, ForeignKey("sync_logs.id", ondelete="SET NULL"), index=True, comment="ID log sinkronisasi terakhir")
    date_synced = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    synced_to_api = Column(Boolean, default=False, comment="Sudah dikirim ke API downstream?")
    local_image_mirrored = Column(Boolean, default=False, comment="Sudah di-mirror ke S3 lokal?")
    local_image_paths = Column(JSON, default={}, comment="Map S3 paths for images")

    def __repr__(self):
        return f"<Assignment(id={self.id[:8]}..., code={self.code_identity})>"


class SyncLog(Base):
    """Log per-run sinkronisasi"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_config_id = Column(String, ForeignKey("survey_configs.id", ondelete="CASCADE"),
                              index=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    total_fetched = Column(Integer, default=0)
    total_new = Column(Integer, default=0)
    total_updated = Column(Integer, default=0)
    total_skipped = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    total_images = Column(Integer, default=0)
    images_mirrored = Column(Integer, default=0)
    status = Column(String, default="running")
    notes = Column(Text)
    timings = Column(JSON, comment="Phase durations in ms")

    def __repr__(self):
        return f"<SyncLog(id={self.id}, status={self.status})>"


class SystemSettings(Base):
    """Pengaturan global / token"""
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SystemSettings(key={self.key})>"
