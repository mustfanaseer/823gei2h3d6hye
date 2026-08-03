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

COBALT_API_URL = os.getenv("COBALT_API_URL", "https://cobalt.tools/api/json")
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
# تحميل الصور
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


# ============================================================
# Instagram
# ============================================================
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
        soup = BeautifulSoup(html, 'html.parser')

        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            if img_url.startswith('http'):
                return download_image_from_url(img_url)

        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                matches = re.findall(r'"display_url":"([^"]+)"', script.string)
                if matches:
                    img_url = matches[0].replace('\\/', '/')
                    if img_url.startswith('http'):
                        return download_image_from_url(img_url)

        return None

    except Exception as e:
        logger.error(f"❌ فشل استخراج الصورة: {e}")
        return None


# ============================================================
# TikTok (طريقة جديدة تعتمد على API)
# ============================================================
def extract_tiktok_image(url):
    """استخراج صورة من TikTok باستخدام API"""
    try:
        logger.info("🖼️ استخراج صورة من TikTok...")
        
        # ====== الطريقة 1: استخدام TikTok API غير رسمي ======
        try:
            # استخدام خدمة خارجية لاستخراج البيانات
            api_url = f"https://www.tikwm.com/api/"
            params = {
                "url": url,
                "count": 1
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and data['data'].get('images'):
                    # تحميل الصورة الأولى
                    img_url = data['data']['images'][0]
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة عبر TikWM")
                        return download_image_from_url(img_url)
                if data.get('data') and data['data'].get('cover'):
                    img_url = data['data']['cover']
                    if img_url.startswith('http'):
                        logger.info(f"✅ تم العثور على صورة عبر TikWM (cover)")
                        return download_image_from_url(img_url)
        except Exception as e:
            logger.warning(f"⚠️ فشل TikWM: {e}")

        # ====== الطريقة 2: استخدام SnapTik API ======
        try:
            api_url = f"https://snaptik.app/abc?url={url}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                # البحث عن الصور في الصفحة
                soup = BeautifulSoup(response.text, 'html.parser')
                img_tags = soup.find_all('img')
                for img in img_tags:
                    src = img.get('src')
                    if src and src.startswith('http') and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        if 'logo' not in src.lower() and 'icon' not in src.lower():
                            logger.info(f"✅ تم العثور على صورة عبر SnapTik")
                            return download_image_from_url(src)
        except Exception as e:
            logger.warning(f"⚠️ فشل SnapTik: {e}")

        # ====== الطريقة 3: استخدام yt-dlp لاستخراج الصورة ======
        try:
            logger.info("🔄 محاولة استخدام yt-dlp لاستخراج الصورة...")
            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    # البحث عن الصورة المصغرة
                    if 'thumbnail' in info:
                        img_url = info['thumbnail']
                        if img_url.startswith('http'):
                            logger.info(f"✅ تم العثور على صورة عبر yt-dlp")
                            return download_image_from_url(img_url)
                    if 'thumbnails' in info and info['thumbnails']:
                        for thumb in info['thumbnails']:
                            if 'url' in thumb:
                                img_url = thumb['url']
                                if img_url.startswith('http'):
                                    logger.info(f"✅ تم العثور على صورة عبر yt-dlp")
                                    return download_image_from_url(img_url)
        except Exception as e:
            logger.warning(f"⚠️ فشل yt-dlp: {e}")

        logger.warning("⚠️ لم يتم العثور على صورة في TikTok")
        return None

    except Exception as e:
        logger.error(f"❌ فشل استخراج الصورة: {e}")
        return None


# ============================================================
# Cobalt API
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
# yt-dlp
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
# pytubefix
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
# دالة تحميل الملف
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
        result = extract_instagram_image(url)
        if result:
            stats["success_count"] += 1
            return result
        
        result = download_via_cobalt(url)
        if result:
            stats["success_count"] += 1
            return result
    
    # ====== TikTok (صورة) ======
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        # 1️⃣ حاول تحميل صورة
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
