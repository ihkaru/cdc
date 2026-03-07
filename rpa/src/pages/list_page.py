from playwright.async_api import Page
import os
from typing import List

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

class ListPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = f"{TARGET_URL}/survey-collection/survey"
        # Locator tabel berdasarkan DataTables HTML
        self.table_rows = "table#Pencacahan tbody tr"
        self.next_button = "a#Pencacahan_next"

    async def get_all_detail_links(self) -> List[str]:
        """Mengambil semua link URL href dari kolom pertama (Nama Survey)"""
        print("Mulai mengekstrak link dari tabel Pencacahan...")
        await self.page.wait_for_selector(self.table_rows)
        
        links = []
        
        # Logika Paginasi Cerdas: Ambil, lalu klik Next sampai habis
        while True:
            # Ambil semua tag <a> di dalam tabel baris saat ini
            elements = await self.page.locator(f"{self.table_rows} td a").element_handles()
            
            for el in elements:
                href = await el.get_attribute("href")
                if href:
                    # Gabungkan domain jika href berupa path relatif
                    full_url = f"{TARGET_URL}{href}" if href.startswith("/") else href
                    links.append(full_url)
            
            # Cek apakah tombol Next bisa diklik (tidak memiliki class 'disabled')
            next_btn = self.page.locator(self.next_button)
            is_disabled = await next_btn.evaluate("el => el.classList.contains('disabled')")
            
            if is_disabled:
                print("Mencapai halaman terakhir dari tabel.")
                break
                
            print("Mengklik halaman tabel selanjutnya...")
            await next_btn.click()
            # Tunggu icon 'processing' hilang (DataTables ajax load)
            await self.page.wait_for_selector("div#Pencacahan_processing", state="hidden")
            
        return links
