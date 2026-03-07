"""
Filter Rotator — Enumerate dan rotate filter pengawas/pencacah
untuk mengatasi limit 1000 baris pada tabel assignment.

Strategi:
- List pengawas/pencacah didapat dari intercept API response
  (survey-period-role-users/region) saat filter wilayah dipilih.
- Dropdown pengawas menampilkan USERNAME (bukan fullname).
- Option text region mengandung kode: "[61] [61] KALIMANTAN BARAT".
- Province+kabupaten di-set sekali di awal; iterasi hanya ganti pengawas.
"""
import asyncio
import re
from typing import AsyncGenerator
from playwright.async_api import Page, Response


# ========== JS CLICK HELPERS ==========

async def _js_click(page: Page, css_selector: str):
    """Klik elemen via JavaScript — bypass viewport."""
    await page.evaluate("""(sel) => {
        const el = document.querySelector(sel);
        if (el) el.click();
    }""", css_selector)


# ========== SIDEBAR ==========

async def open_filter_sidebar(page: Page):
    """Buka sidebar filter jika belum terbuka."""
    is_visible = await page.evaluate("""() => {
        const sidebar = document.querySelector('div.sidebar-content');
        return sidebar && sidebar.offsetParent !== null;
    }""")

    if not is_visible:
        await page.evaluate("""() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.innerText.includes('Filter') &&
                    !btn.innerText.includes('Data') &&
                    !btn.innerText.includes('Reset')) {
                    btn.click();
                    break;
                }
            }
        }""")
        await page.wait_for_selector("div.sidebar-content", state="visible", timeout=5000)
        await asyncio.sleep(0.5)


# ========== REGION DROPDOWN (by CSS name attribute) ==========

async def select_region_dropdown(page: Page, css_selector: str, option_text: str):
    """
    Pilih option di dropdown region.
    Option text bisa partial match — "KALIMANTAN BARAT" akan cocok
    dengan "[61] [61] KALIMANTAN BARAT".
    """
    # Klik toggle
    await _js_click(page, f"{css_selector} .ngx-select__toggle")
    await asyncio.sleep(0.8)

    # Tunggu dropdown muncul
    for _ in range(10):
        has_items = await page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (!el) return false;
            const items = el.querySelectorAll('.dropdown-menu .ngx-select__item');
            return items.length > 0;
        }""", css_selector)
        if has_items:
            break
        await asyncio.sleep(0.5)

    # Klik item yang cocok (partial match, case-insensitive)
    clicked = await page.evaluate("""(args) => {
        const [sel, text] = args;
        const el = document.querySelector(sel);
        if (!el) return false;
        const textLower = text.toLowerCase();
        const items = el.querySelectorAll('.dropdown-menu .ngx-select__item');
        for (const item of items) {
            if (item.innerText.trim().toLowerCase().includes(textLower)) {
                item.click();
                return true;
            }
        }
        return false;
    }""", [css_selector, option_text])

    if not clicked:
        print(f"   ⚠️ Option '{option_text}' tidak ditemukan di {css_selector}")
    else:
        await asyncio.sleep(1.5)  # Tunggu cascading API


# ========== PENGAWAS/PENCACAH DROPDOWN (by index) ==========
# Pengawas & pencacah dropdowns: ngx-select[optiontextfield="-"]
# Index 0 = Pengawas, Index 1 = Pencacah
# Items menampilkan USERNAME, bukan fullname

async def _clear_optiontextfield_dropdown(page: Page, index: int):
    """Clear selection di dropdown by clicking the X button."""
    await page.evaluate("""(idx) => {
        const selects = document.querySelectorAll('ngx-select[optiontextfield="-"]');
        if (selects[idx]) {
            const clearBtn = selects[idx].querySelector('.ngx-select__clear');
            if (clearBtn) clearBtn.click();
        }
    }""", index)
    await asyncio.sleep(0.5)


async def _select_optiontextfield_dropdown(page: Page, index: int, option_text: str):
    """
    Pilih option di dropdown ngx-select[optiontextfield='-'] by index.
    Searches by partial match, case-insensitive.
    """
    # Klik toggle
    await page.evaluate("""(idx) => {
        const selects = document.querySelectorAll('ngx-select[optiontextfield="-"]');
        if (selects[idx]) {
            const toggle = selects[idx].querySelector('.ngx-select__toggle');
            if (toggle) toggle.click();
        }
    }""", index)
    await asyncio.sleep(0.8)

    # Tunggu items muncul
    for _ in range(10):
        has_items = await page.evaluate("""(idx) => {
            const selects = document.querySelectorAll('ngx-select[optiontextfield="-"]');
            if (!selects[idx]) return false;
            const items = selects[idx].querySelectorAll('.dropdown-menu .ngx-select__item');
            return items.length > 0;
        }""", index)
        if has_items:
            break
        await asyncio.sleep(0.5)

    # Klik item yang cocok
    clicked = await page.evaluate("""(args) => {
        const [idx, text] = args;
        const selects = document.querySelectorAll('ngx-select[optiontextfield="-"]');
        if (!selects[idx]) return false;
        const textLower = text.toLowerCase();
        const items = selects[idx].querySelectorAll('.dropdown-menu .ngx-select__item');
        for (const item of items) {
            if (item.innerText.trim().toLowerCase().includes(textLower)) {
                item.click();
                return true;
            }
        }
        return false;
    }""", [index, option_text])

    if not clicked:
        # Tutup dropdown
        await page.keyboard.press("Escape")
        print(f"   ⚠️ Option '{option_text}' tidak ditemukan di dropdown index {index}")
    else:
        await asyncio.sleep(1)


async def select_pengawas(page: Page, username: str):
    """Pilih pengawas di dropdown (index 0) by username."""
    await _select_optiontextfield_dropdown(page, 0, username)


async def select_pencacah(page: Page, username: str):
    """Pilih pencacah di dropdown (index 1) by username."""
    await _select_optiontextfield_dropdown(page, 1, username)


async def clear_pengawas(page: Page):
    """Clear pengawas selection."""
    await _clear_optiontextfield_dropdown(page, 0)


async def clear_pencacah(page: Page):
    """Clear pencacah selection."""
    await _clear_optiontextfield_dropdown(page, 1)


# ========== API INTERCEPTION — GET PENGAWAS/PENCACAH LIST ==========

async def get_user_lists_via_api(
    page: Page,
    provinsi: str,
    kabupaten: str,
) -> tuple[list[dict], list[dict]]:
    """
    Pilih Provinsi + Kabupaten di filter, lalu intercept API response
    'survey-period-role-users/region' untuk mendapatkan daftar pengawas & pencacah.

    Returns:
        (pengawas_list, pencacah_list) — masing-masing list of dicts
    """
    captured_responses: list[list[dict]] = []

    async def on_response(response: Response):
        if 'survey-period-role-users' in response.url and response.status == 200:
            try:
                body = await response.json()
                if body.get('success'):
                    captured_responses.append(body.get('data', []))
            except:
                pass

    page.on('response', on_response)

    try:
        await open_filter_sidebar(page)

        if provinsi:
            await select_region_dropdown(page, "ngx-select[name='region1Id']", provinsi)
            await asyncio.sleep(2)

        if kabupaten:
            await select_region_dropdown(page, "ngx-select[name='region2Id']", kabupaten)
            await asyncio.sleep(4)  # Tunggu API pengawas/pencacah

    finally:
        page.remove_listener('response', on_response)

    # Parse: pisahkan pengawas vs pencacah
    pengawas_list = []
    pencacah_list = []

    for response_data in captured_responses:
        for user in response_data:
            entry = {
                'fullname': user.get('fullname', ''),
                'username': user.get('username', ''),
                'userId': user.get('userId', ''),
                'isPencacah': user.get('isPencacah', False),
                'description': user.get('description', ''),
            }
            if user.get('isPencacah', False):
                pencacah_list.append(entry)
            else:
                pengawas_list.append(entry)

    print(f"   📋 API intercept: {len(pengawas_list)} pengawas, {len(pencacah_list)} pencacah")
    return pengawas_list, pencacah_list


# ========== CLICK BUTTONS ==========

async def click_filter_data(page: Page):
    """Klik tombol 'Filter Data' via JS."""
    await page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            if (btn.innerText.includes('Filter Data')) { btn.click(); break; }
        }
    }""")

    try:
        await page.wait_for_selector("div#assignmentDatatable_processing", state="visible", timeout=3000)
    except:
        pass
    try:
        await page.wait_for_selector("div#assignmentDatatable_processing", state="hidden", timeout=30000)
    except:
        pass
    await asyncio.sleep(0.5)


async def click_reset(page: Page):
    """Klik tombol 'Reset' via JS."""
    await open_filter_sidebar(page)
    await page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            if (btn.innerText.includes('Reset')) { btn.click(); break; }
        }
    }""")
    await asyncio.sleep(1)
    try:
        await page.wait_for_selector("div#assignmentDatatable_processing", state="hidden", timeout=10000)
    except:
        pass


# ========== TOTAL ENTRIES ==========

async def get_total_entries(page: Page) -> int:
    """Baca jumlah total entries dari 'Showing X to Y of Z entries'."""
    try:
        info_text = await page.locator("div#assignmentDatatable_info").inner_text()
        match = re.search(r'of\s+([\d,]+)\s+entries', info_text)
        if match:
            return int(match.group(1).replace(",", ""))
    except:
        pass
    return 0


# ========== MAIN ITERATION LOOP ==========

async def iterate_filters(
    page: Page,
    provinsi: str,
    kabupaten: str,
    rotation: str = "pengawas",
) -> AsyncGenerator[tuple[str, str | None], None]:
    """
    Generator yang yields (pengawas_username, pencacah_username | None).

    Flow:
    1. Set Provinsi + Kabupaten → intercept API → dapatkan daftar pengawas
    2. Klik Filter Data dengan province+kabupaten
    3. Per pengawas: clear & select pengawas → klik Filter Data → cek entries
    4. Jika >1000 → sub-loop per pencacah
    """
    # FASE A: Set region filters dan dapatkan pengawas via API
    pengawas_list, all_pencacah = await get_user_lists_via_api(page, provinsi, kabupaten)

    if not pengawas_list:
        print("   ⚠️ Tidak ada pengawas dari API! Yield tanpa filter pengawas.")
        # Klik Filter Data dengan region saja
        await click_filter_data(page)
        yield ("", None)
        return

    # FASE B: Iterasi per pengawas
    for idx, pengawas in enumerate(pengawas_list):
        pg_username = pengawas['username']
        pg_fullname = pengawas['fullname']
        print(f"\n🔄 [{idx+1}/{len(pengawas_list)}] Pengawas: {pg_fullname} (@{pg_username})")

        # Buka sidebar, clear pengawas lama, select pengawas baru
        await open_filter_sidebar(page)
        await clear_pengawas(page)
        await clear_pencacah(page)
        await select_pengawas(page, pg_username)
        await click_filter_data(page)

        if rotation == "pencacah":
            # Sub-loop per pencacah — intercept pencacah API
            pencacah_list = await _get_pencacah_for_pengawas(page, pengawas)

            if not pencacah_list:
                yield (pg_username, None)
            else:
                for pc in pencacah_list:
                    # Select pencacah
                    await open_filter_sidebar(page)
                    await clear_pencacah(page)
                    await select_pencacah(page, pc['username'])
                    await click_filter_data(page)
                    yield (pg_username, pc['username'])

        else:
            # rotation="pengawas" — cek apakah perlu sub-loop
            total = await get_total_entries(page)
            print(f"   📊 Total entries: {total}")

            if total <= 1000:
                yield (pg_username, None)
            else:
                print(f"   ⚠️ Lebih dari 1000 entries! Sub-loop per pencacah...")
                pencacah_list = await _get_pencacah_for_pengawas(page, pengawas)

                if not pencacah_list:
                    print(f"   ⚠️ Tidak ada pencacah! Yield apa adanya")
                    yield (pg_username, None)
                else:
                    for pc in pencacah_list:
                        await open_filter_sidebar(page)
                        await clear_pencacah(page)
                        await select_pencacah(page, pc['username'])
                        await click_filter_data(page)
                        yield (pg_username, pc['username'])


async def _get_pencacah_for_pengawas(page: Page, pengawas: dict) -> list[dict]:
    """
    Dapatkan list pencacah untuk pengawas tertentu via API intercept.
    Triggered saat pengawas dipilih di dropdown.
    """
    captured: list[dict] = []

    async def on_response(response: Response):
        if 'survey-period-role-users' in response.url and response.status == 200:
            try:
                body = await response.json()
                if body.get('success'):
                    for user in body.get('data', []):
                        if user.get('isPencacah', False):
                            captured.append({
                                'fullname': user.get('fullname', ''),
                                'username': user.get('username', ''),
                            })
            except:
                pass

    page.on('response', on_response)
    try:
        # Re-select pengawas untuk trigger API pencacah
        await open_filter_sidebar(page)
        await clear_pengawas(page)
        await select_pengawas(page, pengawas['username'])
        await asyncio.sleep(3)
    finally:
        page.remove_listener('response', on_response)

    print(f"   📋 Pencacah untuk @{pengawas['username']}: {len(captured)} orang")
    return captured
