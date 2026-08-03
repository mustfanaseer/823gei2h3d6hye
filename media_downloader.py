import os
import time
import re
import requests
import logging
import yt_dlp
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============== جلب رابط Cobalt من ملف .env ==============
COBALT_API_URL = os.getenv("COBALT_API_URL", "https://cobalt.tools/api/json")

# ============== إحصائيات ==============
stats = {"success_count": 0, "fail_count": 0}


def detect_platform(url: str) -> str:
    if "instagram.com" in url:
        return "Instagram 📷"
    elif "tiktok.com" in url or "vt.tiktok.com" in url:
        return "TikTok 🎵"
    elif "youtube.com" in url or "youtu.be" in url:
        return "YouTube ▶️"
    elif "facebook.com" in url:
        return "Facebook 📘"
    else:
        return "رابط خارجي 🌐"


# ============================================================
# 0️⃣ تحميل الصور (طريقة قوية)
# ============================================================
def download_image_from_url(image_url):
    """تحميل صورة من رابط مباشر"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.instagram.com/",
        }

        response = requests.get(image_url, headers=headers, stream=True, timeout=30)
        if response.status_code != 200:
            return None

        ext = image_url.split('.')[-1].split('?')[0]
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
            ext = 'jpg'

        file_path = f"downloads/image_{int(time.time())}.{ext}"
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            logger.info(f"✅ تم تحميل الصورة")
            return file_path

        return None

    except Exception as e:
        logger.error(f"❌ فشل تحميل الصورة: {e}")
        return None


def extract_instagram_image(url):
    """استخراج صورة من Instagram - طريقة محسنة"""
    try:
        logger.info("🖼️ استخراج صورة من Instagram...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.warning(f"⚠️ فشل جلب الصفحة: {response.status_code}")
            return None

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # ====== الطريقة 1: البحث عن meta tag ======
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            if img_url.startswith('http'):
                logger.info(f"✅ تم العثور على صورة في meta tag")
                return download_image_from_url(img_url)

        # ====== الطريقة 2: البحث في الـ Scripts ======
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # البحث عن display_url
                matches = re.findall(r'"display_url":"([^"]+)"', script.string)
                if matches:
                    img_url = matches[0].replace('\\/', '/')
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة في Script")
                        return download_image_from_url(img_url)
                
                # البحث عن display_src
                matches = re.findall(r'"display_src":"([^"]+)"', script.string)
                if matches:
                    img_url = matches[0].replace('\\/', '/')
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة في Script")
                        return download_image_from_url(img_url)

        # ====== الطريقة 3: البحث في JSON ======
        json_pattern = r'<script[^>]+type="text/javascript"[^>]*>([^<]+)</script>'
        json_matches = re.findall(json_pattern, html)
        for script in json_matches:
            if 'display_url' in script:
                matches = re.findall(r'"display_url":"([^"]+)"', script)
                if matches:
                    img_url = matches[0].replace('\\/', '/')
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة في JSON")
                        return download_image_from_url(img_url)

        # ====== الطريقة 4: البحث عن أي صورة في الصفحة ======
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src')
            if src and src.startswith('http') and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                # استبعاد الشعارات والأيقونات الصغيرة
                if 'logo' in src.lower() or 'icon' in src.lower() or 'avatar' in src.lower():
                    continue
                logger.info(f"✅ تم العثور على صورة في img tag")
                return download_image_from_url(src)

        logger.warning("⚠️ لم يتم العثور على صورة في Instagram")
        return None

    except Exception as e:
        logger.error(f"❌ فشل استخراج الصورة: {e}")
        return None


def extract_tiktok_image(url):
    """استخراج صورة من TikTok - طريقة محسنة"""
    try:
        logger.info("🖼️ استخراج صورة من TikTok...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.tiktok.com/",
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.warning(f"⚠️ فشل جلب الصفحة: {response.status_code}")
            return None

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # ====== الطريقة 1: البحث عن meta tag ======
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            if img_url.startswith('http'):
                logger.info(f"✅ تم العثور على صورة في meta tag")
                return download_image_from_url(img_url)

        # ====== الطريقة 2: البحث في الـ Scripts ======
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # البحث عن imageUrl
                matches = re.findall(r'"imageUrl":"([^"]+)"', script.string)
                if matches:
                    img_url = matches[0].replace('\\/', '/')
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة في Script")
                        return download_image_from_url(img_url)
                
                # البحث عن cover
                matches = re.findall(r'"cover":"([^"]+)"', script.string)
                if matches:
                    img_url = matches[0].replace('\\/', '/')
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة في Script")
                        return download_image_from_url(img_url)

        # ====== الطريقة 3: البحث في JSON ======
        json_pattern = r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
        json_match = re.search(json_pattern, html, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if '__DEFAULT_SCOPE__' in data:
                    scope = data['__DEFAULT_SCOPE__']
                    if 'video' in scope and 'cover' in scope['video']:
                        img_url = scope['video']['cover']
                        if img_url.startswith('http'):
                            logger.info(f"✅ تم العثور على صورة في JSON")
                            return download_image_from_url(img_url)
                    if 'image' in scope:
                        img_url = scope['image']
                        if isinstance(img_url, str) and img_url.startswith('http'):
                            logger.info(f"✅ تم العثور على صورة في JSON")
                            return download_image_from_url(img_url)
            except:
                pass

        logger.warning("⚠️ لم يتم العثور على صورة في TikTok")
        return None

    except Exception as e:
        logger.error(f"❌ فشل استخراج الصورة: {e}")
        return None


# ============================================================
# 1️⃣ Cobalt API
# ============================================================
def download_via_cobalt(url):
    """إرسال الرابط إلى Cobalt API"""
    try:
        logger.info(f"📤 [1/3] محاولة Cobalt API: {url}")
        
        payload = {
            "url": url,
            "downloadMode": "auto",
            "videoQuality": "1080",
            "audioFormat": "mp3",
            "alwaysProxy": False
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        api_url = COBALT_API_URL.rstrip('/') + '/'
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") in ["tunnel", "redirect", "success"]:
                download_url = data.get("url")
                if download_url:
                    logger.info(f"✅ Cobalt نجح!")
                    return download_file(download_url)
        else:
            logger.warning(f"⚠️ Cobalt فشل: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Cobalt خطأ: {e}")
        return None


# ============================================================
# 2️⃣ yt-dlp
# ============================================================
def download_with_ytdlp(url):
    """تحميل باستخدام yt-dlp"""
    try:
        logger.info(f"📤 [2/3] محاولة yt-dlp: {url}")
        
        if "/shorts/" in url:
            video_id = url.split("/shorts/")[1].split("?")[0]
            url = f"https://youtube.com/watch?v={video_id}"
            logger.info(f"🔄 تحويل Shorts إلى: {url}")
        
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
            url = f"https://youtube.com/watch?v={video_id}"
            logger.info(f"🔄 تحويل youtu.be إلى: {url}")
        
        opts = {
            "outtmpl": "downloads/ytdlp_%(id)s.%(ext)s",
            "format": "best[ext=mp4]/best",
            "quiet": False,
            "noplaylist": True,
            "ignoreerrors": True,
            "cookiefile": None,
            "extract_flat": False,
            "prefer_insecure": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            "throttledratelimit": 100000000,
            "concurrent_fragment_downloads": 5,
            "extractor_args": {
                "youtube": {
                    "skip": ["hls", "dash"],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if os.path.exists(file_path):
                logger.info(f"✅ yt-dlp نجح!")
                return file_path
            
            for ext in ['.mp4', '.webm', '.mkv']:
                test_path = file_path.rsplit('.', 1)[0] + ext
                if os.path.exists(test_path):
                    logger.info(f"✅ yt-dlp نجح (امتداد مختلف)!")
                    return test_path
                    
        return None
        
    except Exception as e:
        logger.warning(f"⚠️ yt-dlp فشل: {e}")
        return None


# ============================================================
# 3️⃣ pytubefix
# ============================================================
def download_with_pytubefix(url):
    """تحميل YouTube باستخدام pytubefix"""
    try:
        from pytubefix import YouTube
        
        logger.info(f"📤 [3/3] محاولة pytubefix: {url}")
        
        if "/shorts/" in url:
            video_id = url.split("/shorts/")[1].split("?")[0]
            url = f"https://youtube.com/watch?v={video_id}"
            logger.info(f"🔄 تحويل Shorts إلى: {url}")
        
        yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
        
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not stream:
            stream = yt.streams.get_highest_resolution()
        
        if not stream:
            return None
        
        file_path = stream.download(output_path="downloads")
        
        if os.path.exists(file_path):
            logger.info(f"✅ pytubefix نجح!")
            return file_path
        
        return None
        
    except Exception as e:
        logger.warning(f"⚠️ pytubefix فشل: {e}")
        return None


# ============================================================
# دالة تحميل الملف من الرابط
# ============================================================
def download_file(download_url):
    """تحميل الملف من الرابط المباشر"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(download_url, headers=headers, stream=True, timeout=60)
        if response.status_code != 200:
            return None
        
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
            filename = re.sub(r'[^\w\-_. ]', '', filename)
            if len(filename) > 50:
                name, ext = os.path.splitext(filename)
                filename = name[:50] + ext
        else:
            filename = download_url.split('/')[-1].split('?')[0]
            if not filename:
                filename = f"media_{int(time.time())}.mp4"
        
        filename = filename.replace('"', '').replace("'", "").strip()
        if len(filename) < 5:
            filename = f"media_{int(time.time())}.mp4"
        
        file_path = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        return None
            
    except Exception as e:
        logger.error(f"❌ فشل تحميل الملف: {e}")
        return None


# ============================================================
# الواجهة الرئيسية
# ============================================================
def download_media(url, bot=None, owner_id=None):
    """الواجهة الرئيسية - تحميل فيديو أو صورة"""
    platform = detect_platform(url)
    logger.info(f"🚀 بدء تحميل من: {platform}")
    
    # ====== Instagram ======
    if "instagram.com" in url:
        # 1️⃣ حاول تحميل صورة
        logger.info("🖼️ محاولة تحميل صورة من Instagram...")
        result = extract_instagram_image(url)
        if result:
            stats["success_count"] += 1
            return result
        
        # 2️⃣ إذا فشل، جرب Cobalt
        result = download_via_cobalt(url)
        if result:
            stats["success_count"] += 1
            return result
    
    # ====== TikTok ======
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        # 1️⃣ حاول تحميل صورة
        logger.info("🖼️ محاولة تحميل صورة من TikTok...")
        result = extract_tiktok_image(url)
        if result:
            stats["success_count"] += 1
            return result
        
        # 2️⃣ إذا فشل، جرب Cobalt
        result = download_via_cobalt(url)
        if result:
            stats["success_count"] += 1
            return result
    
    # ====== YouTube ======
    if "youtube.com" in url or "youtu.be" in url:
        result = download_via_cobalt(url)
        if result:
            stats["success_count"] += 1
            return result
        
        result = download_with_ytdlp(url)
        if result:
            stats["success_count"] += 1
            return result
        
        result = download_with_pytubefix(url)
        if result:
            stats["success_count"] += 1
            return result
    
    # ====== منصات أخرى ======
    result = download_via_cobalt(url)
    if result:
        stats["success_count"] += 1
        return result
    
    # ====== فشل كل شيء ======
    stats["fail_count"] += 1
    logger.error(f"❌ فشلت جميع طرق التحميل: {url}")
    
    if bot and owner_id:
        try:
            from messages import get_dev_message
            msg = get_dev_message("download_failed", platform=platform, user_id=owner_id)
            import asyncio
            asyncio.create_task(bot.send_message(chat_id=owner_id, text=msg, parse_mode="Markdown"))
        except:
            pass
    
    return None


def get_stats():
    return stats


def reset_stats():
    stats["success_count"] = 0
    stats["fail_count"] = 0


def close_driver():
    logger.info("✅ باستخدام Cobalt + yt-dlp + pytubefix")
