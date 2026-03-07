"""
Survey Navigator — Menemukan survey dan navigasi ke tab Data
"""
import os
import re
from playwright.async_api import Page

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")


async def find_survey_id(page: Page, survey_name: str) -> str | None:
    """
    Cari survey berdasarkan nama di tabel daftar survey.
    Navigasi ke halaman survey list, lalu cari link yang mengandung nama survey.
    
    Returns:
        Survey ID (UUID) atau None jika tidak ditemukan.
    """
    print(f"📋 Mencari survey: '{survey_name}'...")
    await page.goto(f"{TARGET_URL}/survey-collection/survey", wait_until="networkidle")
    
    # Tunggu tabel Pencacahan muncul
    await page.wait_for_selector("table#Pencacahan tbody", timeout=15000)
    
    # Paginasi tabel survey — loop sampai ketemu atau habis
    while True:
        # Cari link dengan teks survey_name di tabel saat ini
        links = await page.locator("table#Pencacahan tbody tr td a").all()
        
        for link in links:
            text = (await link.inner_text()).strip()
            if survey_name.lower() in text.lower():
                href = await link.get_attribute("href")
                # Ekstrak survey ID dari href: /survey-collection/general/{SURVEY_ID}
                match = re.search(r'/general/([a-f0-9\-]+)', href)
                if match:
                    survey_id = match.group(1)
                    print(f"   ✅ Ditemukan: '{text}' → ID: {survey_id}")
                    return survey_id
        
        # Cek apakah ada halaman berikutnya
        next_btn = page.locator("a#Pencacahan_next")
        is_disabled = await next_btn.evaluate("el => el.classList.contains('disabled')")
        
        if is_disabled:
            break
            
        await next_btn.click()
        await page.wait_for_selector("div#Pencacahan_processing", state="hidden")

    print(f"   ❌ Survey '{survey_name}' tidak ditemukan di tabel!")
    return None


async def navigate_to_data_tab(page: Page, survey_id: str) -> bool:
    """
    Navigasi langsung ke tab Data (Collect) survey menggunakan URL langsung.
    
    Returns:
        True jika berhasil, False jika gagal.
    """
    url = f"{TARGET_URL}/survey-collection/collect/{survey_id}"
    print(f"📊 Navigasi ke tab Data: {url}")
    
    try:
        await page.goto(url, wait_until="networkidle")
        
        # Tunggu tabel assignment muncul
        await page.wait_for_selector("table#assignmentDatatable", timeout=15000)
        print("   ✅ Tab Data terbuka, tabel assignment terdeteksi.")
        return True
    except Exception as e:
        print(f"   ❌ Gagal navigasi ke tab Data: {e}")
        return False
