import asyncio
import logging
import os
from datetime import datetime, timezone

import aiohttp

from auth import fetch_vpn_cookie
from crypto import decrypt_password
from db.connection import get_session, init_db, reset_engine
from db.models import SurveyConfig, SystemSettings

logger = logging.getLogger("rpa.connectivity")


class FasihConnectionError(Exception):
    """Raised when VPN or BPS network is fundamentally unreachable."""


TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")


async def check_fasih_reachable() -> tuple[bool, str]:
    """
    Check if FASIH-SM is reachable via the VPN tunnel.
    Uses two signals:
    1. HTTP probe to /oauth_login.html (with SSL bypass for internal cert)
    2. Fallback: check if ppp0 exists and has an IP (tunnel-level check)
    Returns: (is_reachable, reason)
    """
    import ssl

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    logger.debug(f"Probing FASIH-SM endpoint: {TARGET_URL}/oauth_login.html")
    try:
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(
            connector=connector, timeout=aiohttp.ClientTimeout(total=8, connect=5)
        ) as session:
            async with session.get(f"{TARGET_URL}/oauth_login.html", allow_redirects=True) as resp:
                if resp.status in [200, 302, 401, 403]:
                    logger.debug("FASIH-SM HTTP probe succeeded")
                    return True, "Reachable"
                logger.warning(f"FASIH-SM probe returned unexpected HTTP status: {resp.status}")
                return False, f"Unexpected status: {resp.status}"
    except asyncio.TimeoutError:
        logger.warning("FASIH-SM probe HTTP timeout. Checking fallback VPN interfaces...")
        # HTTP timeout — but tunnel might still be fine
        # Check tun0 or ppp0 as secondary signal
        has_vpn = os.path.exists("/sys/class/net/tun0") or os.path.exists("/sys/class/net/ppp0")
        if has_vpn:
            logger.info("VPN interface (tun0/ppp0) is UP. Treating FASIH as reachable (slow response).")
            # Interface exists — tunnel is up, just slow
            return True, "Reachable (VPN UP, HTTP slow)"
        logger.error("No active VPN interface (tun0/ppp0) found on HTTP timeout.")
        return False, "Connection timeout"
    except Exception as e:
        has_vpn = os.path.exists("/sys/class/net/tun0") or os.path.exists("/sys/class/net/ppp0")
        err_type = type(e).__name__
        err_msg = str(e)
        logger.warning(f"FASIH-SM probe error: {err_type} ({err_msg}). Checking fallback VPN interfaces...")
        if has_vpn:
            logger.info("VPN interface (tun0/ppp0) is UP. Treating FASIH as reachable (probe error).")
            return True, f"Reachable (VPN UP, probe error: {err_type})"
        logger.error(f"No active VPN interface (tun0/ppp0) found. FASIH is unreachable: {err_type} {err_msg}")
        return False, f"Connection error: {err_type} {err_msg}".strip()


async def is_session_stale() -> bool:
    """
    Perform a more thorough check: try to reach an API endpoint.
    If it redirects to login, the session (VPN cookie) is stale.
    """
    try:
        # We check a known protected API endpoint
        test_url = f"{TARGET_URL}/survey/api/v1/surveys/datatable?pageSize=1"
        logger.debug(f"Checking session staleness at: {test_url}")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(test_url, allow_redirects=True) as resp:
                # If the final URL contains oauth_login, it's stale
                if "oauth_login.html" in str(resp.url):
                    logger.warning("Session stale! Redirected to login page.")
                    return True
                logger.info(f"Session is active and valid (status: {resp.status})")
                return False
    except Exception as e:
        # If we can't even connect, it's not 'stale', it's 'disconnected'
        logger.error(f"Error checking session staleness: {type(e).__name__} ({e!s})")
        return False


async def ensure_connected():
    """
    Proactive Self-Healing:
    1. Check if FASIH is reachable.
    2. If not, auto-fetch new VPN cookie via Playwright SSO login.
    3. Update DB — VPN watcher (entrypoint.sh) picks it up every 10s.
    4. Poll for reconnect, up to 60s.
    """
    logger.info("Executing connectivity check...")
    reachable, reason = await check_fasih_reachable()

    if reachable:
        logger.info(f"FASIH-SM is reachable: {reason}")
        return True

    logger.warning(f"FASIH unreachable: {reason}. Triggering self-healing workflow...")

    reset_engine()
    init_db()
    session = get_session()
    try:
        # 1. Borrow SSO credentials dari survey aktif
        survey = session.query(SurveyConfig).filter(SurveyConfig.is_active == True).first()
        if not survey:
            raise FasihConnectionError("No active survey found to provide credentials for VPN self-healing.")

        username = survey.sso_username
        password = decrypt_password(survey.sso_password_encrypted)
        logger.info(f"Borrowing SSO credentials for self-healing: {username[:3]}*** from survey '{survey.survey_name}'")

        # 2. Fetch cookie baru via Playwright (VPN portal)
        cookie = await fetch_vpn_cookie(username, password)
        if not cookie:
            logger.error("Failed to fetch new VPN cookie via Playwright.")
            logger.warning("Attempting to proceed with sync (tunnel might recover)...")
            return False

        # 3. Simpan ke DB — VPN entrypoint.sh akan pick up dalam ~10s
        setting = session.query(SystemSettings).filter_by(key="vpn_cookie").first()
        if setting:
            setting.value = cookie
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = SystemSettings(key="vpn_cookie", value=cookie)
            session.add(setting)
        session.commit()
        logger.info("New VPN cookie successfully saved to database. Waiting for VPN tunnel reconnect...")

        # 4. Poll hingga terhubung (maks 90s)
        # VPN watcher: polling setiap 10s → konek: ~15-20s → total maks ~30-40s
        for attempt in range(18):  # 18 × 5s = 90s
            await asyncio.sleep(5)
            r, info = await check_fasih_reachable()
            if r:
                logger.info(f"VPN self-healing success! Reconnected after {(attempt + 1) * 5}s: {info}")
                return True
            logger.warning(f"Still waiting for VPN reconnect [{attempt + 1}/18] — {info}")

        logger.error(f"Cookie updated but FASIH remains unreachable after 90s (last reason: {info})")
        raise FasihConnectionError(f"VPN self-healing failed: BPS Network unreachable ({info})")

    except FasihConnectionError:
        raise
    except Exception as e:
        logger.exception("Unexpected error occurred during VPN self-healing execution")
        raise FasihConnectionError(f"VPN self-healing exception: {e!s}")
    finally:
        session.close()
