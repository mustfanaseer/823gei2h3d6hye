import os
import time
import re
import requests
import logging
import yt_dlp
from dotenv import load_dotenv

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
# 0️⃣ تحميل الصور (جديد)
# ============================================================
def download_image_from_url(image_url):
    """تحميل صورة من رابط مباشر"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
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
    """استخراج صورة من Instagram"""
    try:
        logger.info("🖼️ استخراج صورة من Instagram...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        html = response.text

        patterns = [
            r'"display_url":"([^"]+)"',
            r'"display_src":"([^"]+)"',
            r'"url":"([^"]+\.(jpg|jpeg|png|gif|webp)[^"]*)"',
            r'<meta property="og:image" content="([^"]+)"',
            r'<img[^>]+src="([^"]+\.(jpg|jpeg|png|gif|webp)[^"]*)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        img_url = match[0]
                    else:
                        img_url = match

                    img_url = img_url.replace('\\/', '/')
                    img_url = img_url.replace('\\', '')

                    if img_url.startswith('http') and any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        return download_image_from_url(img_url)

        return None

    except Exception as e:
        logger.error(f"❌ فشل استخراج الصورة: {e}")
        return None


def extract_tiktok_image(url):
    """استخراج صورة من TikTok"""
    try:
        logger.info("🖼️ استخراج صورة من TikTok...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.tiktok.com/",
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        html = response.text

        patterns = [
            r'"imageUrl":"([^"]+)"',
            r'"cover":"([^"]+)"',
            r'"thumb":"([^"]+)"',
            r'"url":"([^"]+\.(jpg|jpeg|png|gif|webp)[^"]*)"',
            r'<meta property="og:image" content="([^"]+)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        img_url = match[0]
                    else:
                        img_url = match

                    img_url = img_url.replace('\\/', '/')
                    img_url = img_url.replace('\\', '')

                    if img_url.startswith('http') and any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        return download_image_from_url(img_url)

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
    
    # ====== الصور (Instagram) ======
    if "instagram.com" in url:
        logger.info("🖼️ محاولة تحميل صورة من Instagram...")
        result = extract_instagram_image(url)
        if result:
            stats["success_count"] += 1
            return result
        
        # إذا فشل، جرب Cobalt
        result = download_via_cobalt(url)
        if result:
            stats["success_count"] += 1
            return result
    
    # ====== الصور (TikTok) ======
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        logger.info("🖼️ محاولة تحميل صورة من TikTok...")
        result = extract_tiktok_image(url)
        if result:
            stats["success_count"] += 1
            return result
        
        # إذا فشل، جرب Cobalt
        result = download_via_cobalt(url)
        if result:
            stats["success_count"] += 1
            return result
    
    # ====== الفيديوهات (YouTube) ======
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
