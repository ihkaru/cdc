"""
Konfigurasi aplikasi — load dari file .env
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env dari folder config/
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path)


@dataclass
class Settings:
    # Login
    sso_username: str = ""
    sso_password: str = ""

    # Survey
    survey_name: str = "PEMUTAKHIRAN DTSEN PBI 2026"

    # Filter wilayah
    filter_provinsi: str = ""
    filter_kabupaten: str = ""
    filter_rotation: str = "pengawas"  # "pengawas" atau "pencacah"

    # Scheduler
    interval_minutes: int = 30

    # Database
    db_path: str = "data/fasih_sync.db"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            sso_username=os.getenv("SSO_USERNAME", ""),
            sso_password=os.getenv("SSO_PASSWORD", ""),
            survey_name=os.getenv("SURVEY_NAME", "PEMUTAKHIRAN DTSEN PBI 2026"),
            filter_provinsi=os.getenv("FILTER_PROVINSI", ""),
            filter_kabupaten=os.getenv("FILTER_KABUPATEN", ""),
            filter_rotation=os.getenv("FILTER_ROTATION", "pengawas"),
            interval_minutes=int(os.getenv("INTERVAL_MINUTES", "30")),
            db_path=os.getenv("DB_PATH", "data/fasih_sync.db"),
        )

    def validate(self) -> list[str]:
        """Validasi konfigurasi, return list error messages."""
        errors = []
        if not self.sso_username:
            errors.append("SSO_USERNAME belum diisi di .env")
        if not self.sso_password:
            errors.append("SSO_PASSWORD belum diisi di .env")
        if not self.survey_name:
            errors.append("SURVEY_NAME belum diisi di .env")
        if self.filter_rotation not in ("pengawas", "pencacah"):
            errors.append("FILTER_ROTATION harus 'pengawas' atau 'pencacah'")
        return errors


# Singleton
settings = Settings.from_env()
