from typing import Optional
from pydantic import BaseModel

class SyncRequest(BaseModel):
    survey_config_id: str
    survey_name: str
    sso_username: str
    sso_password: str  # Already decrypted by dashboard
    filter_provinsi: str = ""
    filter_kabupaten: str = ""
    filter_rotation: str = "pengawas"


class SyncResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[int] = None
    queue_position: Optional[int] = None


class StatusResponse(BaseModel):
    is_running: bool
    current_survey: Optional[str] = None
    current_job_id: Optional[int] = None
    started_at: Optional[str] = None
    last_result: Optional[dict] = None
    queue: list = []
    progress: Optional[dict] = None


class ProbeRequest(BaseModel):
    sso_username: str
    sso_password: str
    survey_name: str
    filter_provinsi: str = ""
    filter_kabupaten: str = ""


class LookupRequest(BaseModel):
    sso_username: str
    sso_password: str


class KabupatenLookupRequest(BaseModel):
    sso_username: str
    sso_password: str
    prov_full_code: str   # e.g. "61"


class VpnCookieRequest(BaseModel):
    sso_username: str
    sso_password: str
