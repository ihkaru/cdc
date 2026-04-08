import os
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime, timezone

from db.connection import get_session, init_db, reset_engine
from db.models import SurveyConfig, SystemSettings
from crypto import decrypt_password
from auth import fetch_vpn_cookie

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

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=8, connect=5)
        ) as session:
            async with session.get(
                f"{TARGET_URL}/oauth_login.html",
                allow_redirects=True
            ) as resp:
                if resp.status in [200, 302, 401, 403]:
                    return True, "Reachable"
                return False, f"Unexpected status: {resp.status}"
    except asyncio.TimeoutError:
        # HTTP timeout — but tunnel might still be fine
        # Check ppp0 as secondary signal
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        if has_ppp:
            # Interface exists — tunnel is up, just slow
            return True, "Reachable (ppp0 UP, HTTP slow)"
        return False, "Connection timeout"
    except Exception as e:
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        err_type = type(e).__name__
        err_msg = str(e)
        if has_ppp:
            return True, f"Reachable (ppp0 UP, probe error: {err_type})"
        return False, f"Connection error: {err_type} {err_msg}".strip()


async def is_session_stale() -> bool:
    """
    Perform a more thorough check: try to reach an API endpoint.
    If it redirects to login, the session (VPN cookie) is stale.
    """
    try:
        # We check a known protected API endpoint
        test_url = f"{TARGET_URL}/survey/api/v1/surveys/datatable?pageSize=1"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(test_url, allow_redirects=True) as resp:
                # If the final URL contains oauth_login, it's stale
                if "oauth_login.html" in str(resp.url):
                    return True
                return False
    except Exception:
        # If we can't even connect, it's not 'stale', it's 'disconnected'
        return False

async def ensure_connected():
    """
    Proactive Self-Healing:
    1. Check if FASIH is reachable.
    2. If not, auto-fetch new VPN cookie via Playwright SSO login.
    3. Update DB — VPN watcher (entrypoint.sh) picks it up every 10s.
    4. Poll for reconnect, up to 60s.
    """
    reachable, reason = await check_fasih_reachable()

    if reachable:
        return True

    print(f"⚠️ FASIH unreachable: {reason}")
    print("🔄 Self-healing: auto-fetching new VPN cookie via Playwright...")

    reset_engine()
    init_db()
    session = get_session()
    try:
        # 1. Borrow SSO credentials dari survey aktif
        survey = session.query(SurveyConfig).filter(SurveyConfig.is_active == True).first()
        if not survey:
            print("   ❌ Tidak ada survey aktif untuk digunakan sebagai kredensial VPN refresh.")
            print("   ⚠️  Melanjutkan sync meski VPN mungkin bermasalah...")
            return False

        username = survey.sso_username
        password = decrypt_password(survey.sso_password_encrypted)
        print(f"   🔑 Menggunakan kredensial: {username[:3]}*** dari survey '{survey.name}'")

        # 2. Fetch cookie baru via Playwright (VPN portal)
        cookie = await fetch_vpn_cookie(username, password)
        if not cookie:
            print("   ❌ Gagal mendapatkan VPN cookie via Playwright.")
            print("   ⚠️  Melanjutkan sync — mungkin VPN masih bisa terhubung...")
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
        print("   ✅ Cookie baru tersimpan di DB. Menunggu VPN tunnel reconnect...")

        # 4. Poll hingga terhubung (maks 60s)
        # VPN watcher: polling setiap 10s → konek: ~15-20s → total maks ~30-40s
        for attempt in range(12):  # 12 × 5s = 60s
            await asyncio.sleep(5)
            r, info = await check_fasih_reachable()
            if r:
                print(f"   ✨ VPN reconnected setelah {(attempt+1)*5}s! ({info})")
                return True
            print(f"   ⏳ Menunggu reconnect... [{attempt+1}/12] — {info}")

        print("   ⚠️ Cookie diperbarui tapi FASIH masih unreachable setelah 60s.")
        print("   ⚠️  Melanjutkan sync — mungkin tunnel sudah up tapi check belum stabil...")
        return False

    except Exception as e:
        print(f"   ❌ Self-healing error: {e}")
        return False
    finally:
        session.close()
