import json
import asyncio
import aiohttp
import os
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, cast, Text, update, or_

from db.connection import get_session
from db.models import Assignment, SurveyConfig
from storage import upload_image

# Domain pattern for BPS images (can be fasih-sm.bps.go.id or bucket1.cloud.bps.go.id)
BPS_DOMAIN_PATTERN = r"(bps\.go\.id|cloud\.bps\.go\.id)"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CDC-Archiver")

async def download_image(url: str) -> bytes | None:
    """Download image content from remote URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://fasih-sm.bps.go.id/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=45) as resp:
                if resp.status == 200:
                    return await resp.read()
                
                if resp.status == 403:
                    logger.error(f"   🚫 [Archiver] 403 Forbidden: Image link expired. URL: {url[:100]}...")
                elif resp.status == 404:
                    logger.error(f"   ❓ [Archiver] 404 Not Found: Image deleted from BPS. URL: {url[:100]}...")
                else:
                    logger.error(f"   ❌ [Archiver] Failed (HTTP {resp.status}): {url[:100]}...")
    except Exception as e:
        logger.error(f"Error downloading image {url}: {e}")
    return None

from extractors.json_logic import extract_variables_from_json

async def mirror_assignment_images(db: Session, assignment: Assignment, rpa=None):
    """
    Find all photo URLs in assignment data, download them,
    and mirror them to local SeaweedFS S3 storage.
    """
    log_prefix = f"   [ARCHIVER:{assignment.id[:8]}]"
    try:
        # Ultra-Robust Greedy JSON Unpacker
        def greedy_unpack(val):
            if not isinstance(val, str): return val
            import re
            # Find the true JSON boundaries even if there's leading/trailing garbage
            match = re.search(r'(\{.*\}|\[.*\])', val, re.DOTALL)
            if match:
                potential_json = match.group(1)
                try:
                    unpacked = json.loads(potential_json)
                    return greedy_unpack(unpacked) # Recursive until DICT/LIST
                except:
                    # If it's escaped JSON (has \"), try unescaping and loading
                    if '\\"' in potential_json:
                        try:
                            # Use a trick to unescape: json.loads('"' + str + '"')
                            # but simpler to just try a replacement or raw load
                            unescaped = potential_json.encode('utf-8').decode('unicode_escape')
                            # Sometimes unicode_escape leaves extra quotes
                            if unescaped.startswith('"') and unescaped.endswith('"'):
                                unescaped = unescaped[1:-1]
                            return greedy_unpack(json.loads(unescaped))
                        except: pass
            return val

        data_json = greedy_unpack(assignment.data_json)
        
        logger.info(f"{log_prefix} 🚀 Starting mirroring process (Status: {assignment.assignment_status_alias})")
        
        async def perform_mirroring(data):
            if isinstance(data, str):
                try: data = json.loads(data)
                except: return False, {}, False
            
            vars_map = extract_variables_from_json(data)
            mirrored_paths = {}
            any_success = False
            has_403 = False
            
            for key, value in vars_map.items():
                if isinstance(value, str) and value.startswith("http"):
                    is_image = (
                        any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']) or
                        any(kw in key.lower() or kw in value.lower() for kw in ['foto', 'image', 'media', 'download'])
                    )
                    
                    if is_image:
                        ext = "jpg"
                        if ".png" in value.lower(): ext = "png"
                        elif ".webp" in value.lower(): ext = "webp"
                        clean_filename = f"{assignment.id}/{key}.{ext}"
                        
                        logger.info(f"{log_prefix} 🔎 Mirroring '{key}' (Source: {str(value)[:60]}...)")
                        content = await download_image(value)
                        
                        if content:
                            local_path = await upload_image(content, clean_filename)
                            mirrored_paths[key] = local_path
                            any_success = True
                            logger.info(f"{log_prefix}      ✅ Mirrored successfully -> {local_path}")
                        else:
                            has_403 = True
                            logger.warning(f"{log_prefix}      ❌ Download failed for {key}")
            
            # Regex Scraper pass (Safety Net)
            import re
            data_str = json.dumps(data)
            img_pattern = r'https?://[^\s"\'<>]+(?:jpg|jpeg|png|webp|gif|foto)[^\s"\'<>]*'
            image_urls = re.findall(img_pattern, data_str, re.IGNORECASE)
            
            if image_urls:
                image_urls = [u for u in image_urls if not any(u.lower().endswith(bad) for bad in ['.pdf', '.json', '.txt'])]
            
            for i, url in enumerate(image_urls):
                if any(url in str(v) for v in vars_map.values()) or any(url == val for val in mirrored_paths.values()):
                    continue
                key = f"scraped_{i}"
                logger.info(f"{log_prefix} [Scraping] {key}... URL: {url[:60]}...")
                content = await download_image(url)
                if content:
                    ext = "jpg"; 
                    if ".png" in url.lower(): ext = "png"
                    clean_filename = f"{assignment.id}/{key}.{ext}"
                    local_path = await upload_image(content, clean_filename)
                    mirrored_paths[key] = local_path
                    any_success = True
                    logger.info(f"{log_prefix}      ✅ Mirrored (Scraped): {local_path}")
                else:
                    has_403 = True
            
            return any_success, mirrored_paths, has_403

        # Helper to extract date/version from URL
        def get_url_date(url):
            import re
            match = re.search(r"X-Amz-Date=(\d{8})", url or "", re.IGNORECASE)
            if match: return match.group(1)
            match = re.search(r"202\d{5}", url or "")
            return match.group(0) if match else "00000000"

        # Execute Pass 1
        success, paths, found_403 = await perform_mirroring(data_json)
        
        # --- HEALING PASS ---
        if found_403 and rpa:
            logger.info(f"{log_prefix} ⚠️ Detected expired links (403). Attempting self-healing phase...")
            try:
                import re
                vars_map = extract_variables_from_json(data_json)

                # Collect filenames of ALL BPS image URLs (not just ones in paths dict,
                # since paths only contains successful downloads — failures are absent)
                file_names_to_refresh = []
                for key, value in vars_map.items():
                    if isinstance(value, str) and "bps.go.id" in value and value.startswith("http"):
                        fn = value.split("/")[-1].split("?")[0]
                        if fn and fn not in file_names_to_refresh:
                            file_names_to_refresh.append(fn)

                # Regex scraper fallback for deeply nested/stringified URLs
                try:
                    data_str = json.dumps(data_json)
                    scraped = re.findall(r'https?://[^\s"\'<>]+bps\.go\.id[^\s"\'<>]+', data_str)
                    for u in scraped:
                        fn = u.split("/")[-1].split("?")[0]
                        if fn and fn not in file_names_to_refresh:
                            file_names_to_refresh.append(fn)
                except: pass

                fresh_urls_map = {}
                if file_names_to_refresh:
                    logger.info(f"{log_prefix} 💊 [Healing] Requesting refresh for {len(file_names_to_refresh)} files via RPA API...")
                    new_urls = await rpa.get_fresh_image_urls(
                        assignment.survey_period_id,
                        [{"assignmentId": assignment.id, "fileNames": file_names_to_refresh}]
                    )

                    if new_urls:
                        logger.info(f"{log_prefix} ✨ [Healing] Received {len(new_urls)} fresh URLs from API.")
                        for old_fn in file_names_to_refresh:
                            fresh = new_urls.get(old_fn)
                            if not fresh:
                                for n_fn, n_url in new_urls.items():
                                    if old_fn in n_fn or n_fn in old_fn:
                                        fresh = n_url
                                        break
                            if fresh:
                                fresh_urls_map[old_fn] = fresh
                                logger.info(f"{log_prefix} 🔗 [Healing] Mapped {old_fn} -> Fresh (Date: {get_url_date(fresh)})")
                            else:
                                logger.warning(f"{log_prefix} ⚠️ [Healing] No fresh URL for {old_fn}")
                    else:
                        logger.warning(f"{log_prefix} ⚠️ [Healing] API returned no fresh URLs.")

                if fresh_urls_map:
                    def perform_global_substitution(data_obj, urls_map):
                        import re
                        try:
                            original_str = json.dumps(data_obj)
                            new_str = original_str
                            sub_count = 0
                            
                            for fname, fresh_url in urls_map.items():
                                # Regex that handles escaped slashes and various delimiters
                                # Match until quote, whitespace, or bracket
                                pattern = rf'https?[^"\'\s<>\\\[\]]*?{re.escape(fname)}[^"\'\s<>\\\[\]]*'
                                
                                matches = re.findall(pattern, new_str)
                                for m in set(matches):
                                    # Keep original escaping style for the replacement URL
                                    repl = fresh_url
                                    if "\\/" in m:
                                        repl = fresh_url.replace("/", "\\/")
                                    
                                    new_str = new_str.replace(m, repl)
                                    sub_count += 1
                                    logger.info(f"{log_prefix} 🛠️ [Substitution] SUCCESS: {fname}")
                                    
                            if sub_count > 0:
                                return json.loads(new_str), True
                        except Exception as e:
                            logger.error(f"{log_prefix} ❌ [Substitution] Failure: {e}")
                        return data_obj, False

                    logger.info(f"{log_prefix} 🛠️ [Archiver] Initiating global URL substitution pass for assignment {assignment.id}...")
                    fresh_data_json, replaced = perform_global_substitution(data_json, fresh_urls_map)
                    
                    if replaced:
                        logger.info(f"{log_prefix} 🚀 Substitution complete! Retrying mirror pass...")
                        success, paths, _ = await perform_mirroring(fresh_data_json)
                        if success:
                            assignment.data_json = fresh_data_json
                            logger.info(f"{log_prefix} ✅ Healing successful. data_json updated.")
                    else:
                        logger.warning(f"{log_prefix} ⚠️ [Healing] Global substitution found no matches to replace.")
                        success = False
                else:
                    # If no healing was attempted/needed, just use the result from first pass
                    pass

            except Exception as e:
                logger.error(f"{log_prefix} ❌ Healing phase failed: {e}")

        # --- COMMIT STRATEGY ---
        # Mark as mirrored=True if:
        #   (a) At least one image was successfully saved to vault, OR
        #   (b) No 403 was found at all — meaning the source genuinely has no image links.
        #
        # If 403s were found but healing failed, do NOT mark as mirrored — retry next cycle.
        if success:
            assignment.local_image_mirrored = True
            assignment.local_image_paths = paths
            db.add(assignment)
            db.commit()
            logger.info(f"{log_prefix} ✅ Mirrored {len(paths)} images to vault.")
            return True
        elif not found_403:
            # No images in source AND no 403 errors — genuinely image-free, mark as checked
            assignment.local_image_mirrored = True
            assignment.local_image_paths = {}
            db.add(assignment)
            db.commit()
            logger.info(f"{log_prefix} ℹ️ No images found (empty). Marked as checked.")
            return True
        else:
            # found_403=True && success=False → healing failed, leave unmirrored for retry
            logger.warning(f"{log_prefix} ⏳ 403 healing failed — will retry next cycle.")
            return False

    except Exception as e:
        logger.error(f"Error mirroring assignment {assignment.id}: {e}")
        db.rollback()
        return False

async def archiver_worker():
    """Main worker loop to process pending images."""
    logger.info("🚀 CDC Image Archiver Worker Started")
    
    while True:
        try:
            db = get_session()

            # --- PASS 1: Only fetch assignments that actually contain image URLs ---
            # Filter at SQL level using LIKE on data_json text to avoid loading
            # thousands of image-free records into Python (2165 → ~147 instantly).
            IMAGE_DOMAINS = [
                "%bucket1.cloud.bps.go.id%",
                "%fasih-sm.bps.go.id%",
            ]
            has_image_url = or_(*[
                cast(Assignment.data_json, Text).like(domain)
                for domain in IMAGE_DOMAINS
            ])

            stmt = select(Assignment).where(
                and_(
                    Assignment.local_image_mirrored == False,
                    has_image_url,
                )
            ).limit(100)
            
            pending = db.scalars(stmt).all()

            # --- PASS 2: Bulk-mark image-free assignments as checked ---
            # Run EVERY iteration (not only when pending is empty) so image-free records
            # don't get stuck waiting behind a 403 retry loop.
            bulk_clear = update(Assignment).where(
                and_(
                    Assignment.local_image_mirrored == False,
                    ~has_image_url,
                )
            ).values(local_image_mirrored=True, local_image_paths={})
            result = db.execute(bulk_clear)
            if result.rowcount > 0:
                db.commit()
                logger.info(f"✅ Bulk-cleared {result.rowcount} image-free assignments.")

            if not pending:
                db.close()
                await asyncio.sleep(20)  # Idle
                continue

            logger.info(f"Processing {len(pending)} image-containing assignments for mirroring...")
            db.close()

            # Initialize RPA client payload
            from api_client import FasihApiClient
            from db.models import SystemSettings
            
            # Fetch SSO session cookies saved by RPA after last successful login.
            # These are required to download from bucket1.cloud.bps.go.id (FASIH S3).
            # vpn_cookie (SVPNCOOKIE) is only for routing — NOT for S3 auth.
            tmp_db = get_session()
            sso_setting = tmp_db.execute(select(SystemSettings).where(SystemSettings.key == "sso_cookies")).scalar_one_or_none()
            tmp_db.close()

            cookies_dict = None
            if sso_setting:
                import json as _json
                try:
                    cookies_dict = _json.loads(sso_setting.value)
                    logger.info(f"   🔑 [Archiver] SSO cookies loaded ({len(cookies_dict)} cookies). Healing capability: ENABLED.")
                except Exception as ce:
                    logger.warning(f"   ⚠️ [Archiver] Failed to parse sso_cookies: {ce}")
            else:
                logger.warning("   ⚠️ [Archiver] No 'sso_cookies' in system_settings. Run a Sync first to populate. Healing: DISABLED.")

            semaphore = asyncio.Semaphore(10)
            
            async def limited_mirror(assignment_id):
                async with semaphore:
                    task_db = get_session()
                    try:
                        # Re-fetch assignment since we closed the main session
                        assignment = task_db.query(Assignment).get(assignment_id)
                        if not assignment:
                            return
                            
                        # Unique RPA Client per task
                        rpa_client = FasihApiClient(cookies_dict) if cookies_dict else None
                        
                        if rpa_client:
                            async with rpa_client as rpa:
                                processed_ok = await mirror_assignment_images(task_db, assignment, rpa=rpa)
                        else:
                            processed_ok = await mirror_assignment_images(task_db, assignment, rpa=None)
                        
                        # Only increment progress if it was successfully marked as mirrored
                        if processed_ok and assignment.sync_log_id:
                             log_id = assignment.sync_log_id
                             count_to_add = len(assignment.local_image_paths) if assignment.local_image_paths else 0
                             if count_to_add > 0:
                                 from sqlalchemy import text
                                 task_db.execute(
                                     text("UPDATE sync_logs SET images_mirrored = images_mirrored + :cnt WHERE id = :log_id"),
                                     {"cnt": count_to_add, "log_id": log_id}
                                 )
                                 task_db.commit()
                    except Exception as e:
                        logger.error(f"   ❌ Mirroring task error for {assignment_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        task_db.rollback()
                    finally:
                        task_db.close()

            # Process the batch using IDs instead of detached objects
            await asyncio.gather(*(limited_mirror(a.id) for a in pending))
            logger.info(f"Batch complete. Continuing loop...")
            
        except Exception as e:
            logger.error(f"Archiver loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(archiver_worker())
