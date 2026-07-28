import os
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============== جلب رابط Cobalt من ملف .env ==============
COBALT_API_URL = os.getenv("COBALT_API_URL", "https://cobalt-api-production-c677.up.railway.app/")

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


def download_via_cobalt(url):
    """إرسال الرابط إلى Cobalt API واستلام رابط التحميل المباشر"""
    try:
        logger.info(f"📤 إرسال الرابط إلى Cobalt: {url}")
        
        payload = {
            "url": url,
            "downloadMode": "auto",
            "videoQuality": "1080",
            "audioFormat": "mp3",
            "alwaysProxy": False
        }
        
        # ✅ إضافة الـ Headers المطلوبة
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
                    logger.info(f"✅ تم استلام رابط التحميل من Cobalt")
                    return download_file(download_url)
                else:
                    logger.error("❌ لم يتم العثور على رابط التحميل")
                    return None
            else:
                error_msg = data.get("text", "خطأ غير معروف")
                logger.error(f"❌ فشل التحميل: {error_msg}")
                return None
        else:
            logger.error(f"❌ خطأ في الاتصال بـ Cobalt: {response.status_code}")
            logger.error(f"📄 الرد: {response.text[:200]}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("❌ انتهى وقت الاتصال بـ Cobalt")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        return None


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
        
        # تنظيف اسم الملف
        filename = filename.replace('"', '').replace("'", "")
        
        file_path = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            logger.info(f"✅ تم تحميل الملف: {filename}")
            return file_path
        else:
            return None
            
    except Exception as e:
        logger.error(f"❌ فشل تحميل الملف: {e}")
        return None


def download_media(url, bot=None, owner_id=None):
    """الواجهة الرئيسية للتحميل"""
    platform = detect_platform(url)
    logger.info(f"🚀 بدء تحميل من: {platform} باستخدام Cobalt API")
    
    result = download_via_cobalt(url)
    if result:
        stats["success_count"] += 1
        return result
    
    stats["fail_count"] += 1
    logger.warning("⚠️ فشل التحميل عبر Cobalt")
    
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
    logger.info("✅ باستخدام Cobalt API (لا يحتاج متصفح)")