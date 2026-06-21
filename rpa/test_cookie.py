import asyncio
import os

from src.auth import fetch_vpn_cookie


async def main():
    username = os.getenv("VPN_USER")
    password = os.getenv("VPN_PASS")

    if not username or not password:
        print("❌ Error: VPN_USER or VPN_PASS not set in environment.")
        return

    print(f"🚀 Testing SVPNCOOKIE fetch for: {username}")
    cookie = await fetch_vpn_cookie(username, password)

    if cookie:
        print(f"✅ SUCCESS! Cookie: {cookie[:20]}...")
    else:
        print("❌ FAILED to get cookie.")


if __name__ == "__main__":
    asyncio.run(main())
