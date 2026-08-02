import os
import time
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
# 1️⃣ Cobalt API (المحاولة الأولى)
# ============================================================
def download_via_cobalt(url):
    """إرسال الرابط إلى Cobalt API"""
    try:
        logger.info(f"📤 [1/2] محاولة Cobalt API: {url}")
        
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
# 2️⃣ yt-dlp (المحاولة الثانية - مخصص لـ YouTube)
# ============================================================
def download_with_ytdlp(url):
    """تحميل YouTube (بما فيها Shorts) باستخدام yt-dlp بدون كوكيز"""
    try:
        logger.info(f"📤 [2/2] محاولة yt-dlp: {url}")
        
        # ✅ تحويل Shorts إلى رابط عادي
        if "/shorts/" in url:
            video_id = url.split("/shorts/")[1].split("?")[0]
            url = f"https://youtube.com/watch?v={video_id}"
            logger.info(f"🔄 تحويل Shorts إلى: {url}")
        
        # ✅ إذا كان الرابط مختصر (youtu.be)
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
            url = f"https://youtube.com/watch?v={video_id}"
            logger.info(f"🔄 تحويل youtu.be إلى: {url}")
        
        # ✅ إعدادات yt-dlp المحسنة
        opts = {
            "outtmpl": "downloads/ytdlp_%(id)s.%(ext)s",
            "format": "best[ext=mp4]/best",
            "quiet": False,
            "noplaylist": True,
            "ignoreerrors": True,
            "cookiefile": None,  # ❌ بدون كوكيز
            "extract_flat": False,
            "prefer_insecure": True,  # ✅ لتجاوز بعض القيود
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            },
            "throttledratelimit": 100000000,
            "concurrent_fragment_downloads": 5,
            # ✅ إعدادات إضافية لـ YouTube Shorts
            "extractor_args": {
                "youtube": {
                    "skip": ["hls", "dash"],  # تجنب بعض التنسيقات
                }
            }
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if os.path.exists(file_path):
                logger.info(f"✅ yt-dlp نجح!")
                return file_path
            
            # البحث بامتدادات أخرى
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
        else:
            filename = download_url.split('/')[-1].split('?')[0]
            if not filename:
                filename = f"media_{int(time.time())}.mp4"
        
        filename = filename.replace('"', '').replace("'", "")
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
    """الواجهة الرئيسية - تجربة طريقتين"""
    platform = detect_platform(url)
    logger.info(f"🚀 بدء تحميل من: {platform}")
    
    # ====== 1️⃣ المحاولة الأولى: Cobalt ======
    result = download_via_cobalt(url)
    if result:
        stats["success_count"] += 1
        return result
    
    # ====== 2️⃣ المحاولة الثانية: yt-dlp (لـ YouTube فقط) ======
    if "youtube.com" in url or "youtu.be" in url:
        logger.info("🔄 استخدام yt-dlp كحل احتياطي لـ YouTube...")
        result = download_with_ytdlp(url)
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
    logger.info("✅ باستخدام Cobalt + yt-dlp")
