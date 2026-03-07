import os
from playwright.async_api import Page

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = f"{TARGET_URL}/oauth_login.html"
        # Locator berdasarkan HTML yang dikirim
        self.sso_bps_button = "a.login-button:has-text('Login SSO BPS')"
        self.sso_eksternal_button = "a.login-button:has-text('Login SSO Eksternal')"

    async def navigate(self):
        print(f"Membuka halaman login: {self.url}")
        await self.page.goto(self.url)
        await self.page.wait_for_load_state("networkidle")

    async def login_sso_bps(self):
        print("Mengklik tombol Login SSO BPS...")
        await self.page.click(self.sso_bps_button)
        # Catatan: Setelah ini kemungkinan akan diredirect ke halaman login Microsoft/SSO BPS asli
        # yang butuh input email & password. Script ini akan dilanjut setelah alur SSO diketahui.
