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
    job_id: int | None = None
    queue_position: int | None = None


class StatusResponse(BaseModel):
    is_running: bool
    is_vpn_fetching: bool
    current_survey: str | None = None
    current_survey_config_id: str | None = None
    current_job_id: int | None = None
    started_at: str | None = None
    last_result: dict | None = None
    queue: list = []
    progress: dict | None = None


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
    prov_full_code: str  # e.g. "61"


class VpnCookieRequest(BaseModel):
    sso_username: str
    sso_password: str
