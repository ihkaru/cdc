"""
Database connection — PostgreSQL via SQLAlchemy.
Falls back to SQLite for local development.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Get database URL from environment, fallback to SQLite."""
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url
    # Fallback: SQLite for local dev
    db_path = os.environ.get("DB_PATH", "data/fasih_sync.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f"sqlite:///{db_path}"


def get_engine(database_url: str = ""):
    global _engine
    if _engine is None:
        url = database_url or get_database_url()
        kwargs = {"echo": False}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session_factory(database_url: str = "") -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionLocal


def get_session(database_url: str = "") -> Session:
    factory = get_session_factory(database_url)
    return factory()


def init_db(database_url: str = ""):
    """Create all tables if they don't exist."""
    from .models import Base
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)


def reset_engine():
    """Reset engine (for switching databases between runs) and gracefully close connections to prevent leaks."""
    global _engine, _SessionLocal
    if _engine is not None:
        try:
            _engine.dispose()
            print("🚰 Pool connections gracefully disposed.")
        except Exception as e:
            print(f"⚠️ Error disposing engine: {e}")
            
    _engine = None
    _SessionLocal = None
