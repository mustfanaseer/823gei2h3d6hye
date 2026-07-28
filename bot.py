import os
import sys
import asyncio
import sqlite3
import logging
import subprocess
import atexit
import time
import threading
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from media_downloader import (
    detect_platform,
    download_media,
    get_stats,
    reset_stats,
    close_driver,
)
from messages import (
    get_welcome,
    get_success,
    get_error,
    get_loading,
    get_invalid_url,
    get_dev_message,
)
from dotenv import load_dotenv

load_dotenv()

# ============== الإعدادات ==============
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
CLEANUP_HOURS = int(os.getenv("CLEANUP_HOURS", 1))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "sorx_baghdad")

if not BOT_TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود!")
    sys.exit(1)

if not OWNER_ID:
    print("❌ خطأ: OWNER_ID غير موجود!")
    sys.exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============== المتغيرات العامة ==============
session_manager = None


# ============== تحديث البوت ==============
def update_ytdlp():
    """تحديث البوت"""
    try:
        logger.info("🔄 جاري التحقق من تحديثات...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if "Successfully installed" in result.stdout:
            return True, "✅ تم تحديث البوت بنجاح!"
        else:
            return True, "✅ البوت محدث بالفعل!"
    except Exception as e:
        return False, f"❌ فشل التحديث: {str(e)[:100]}"


def auto_update():
    success, message = update_ytdlp()
    print(f"{message}")


# ============== دوال التنظيف ==============
def clean_old_files():
    try:
        downloads_dir = "downloads"
        if os.path.exists(downloads_dir):
            now = datetime.now()
            deleted_count = 0
            for filename in os.listdir(downloads_dir):
                file_path = os.path.join(downloads_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (now - file_time) > timedelta(hours=CLEANUP_HOURS):
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except:
                            pass
            if deleted_count > 0:
                logger.info(f"🗑️ تم تنظيف {deleted_count} ملف قديم")
            return deleted_count
    except:
        pass
    return 0


def start_cleanup_scheduler():
    def cleanup_loop():
        while True:
            try:
                time.sleep(3600)
                clean_old_files()
            except:
                pass
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info("🔄 تم تشغيل التنظيف التلقائي (كل ساعة)")


# ============== جدول التقرير اليومي ==============
def start_daily_report_scheduler(bot):
    def report_loop():
        while True:
            try:
                now = datetime.now()
                tomorrow = now + timedelta(days=1)
                midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
                wait_seconds = (midnight - now).total_seconds()
                time.sleep(wait_seconds)

                stats = get_stats()
                used_space = 0
                temp_files = 0
                if os.path.exists("downloads"):
                    for f in os.listdir("downloads"):
                        path = os.path.join("downloads", f)
                        if os.path.isfile(path):
                            used_space += os.path.getsize(path)
                            temp_files += 1

                msg = get_dev_message(
                    "daily_report",
                    date=datetime.now().strftime("%Y-%m-%d"),
                    success_count=stats["success_count"],
                    fail_count=stats["fail_count"],
                    used_space=round(used_space / (1024 * 1024), 2),
                    temp_files=temp_files,
                    user_id=OWNER_ID
                )

                import asyncio
                asyncio.run(bot.send_message(chat_id=OWNER_ID, text=msg, parse_mode="Markdown"))
                reset_stats()

            except Exception as e:
                logger.error(f"خطأ في التقرير اليومي: {e}")

    thread = threading.Thread(target=report_loop, daemon=True)
    thread.start()
    logger.info("📊 تم تشغيل التقرير اليومي (منتصف الليل)")


# ============== قاعدة البيانات ==============
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
c.execute("CREATE TABLE IF NOT EXISTS channels (channel TEXT PRIMARY KEY)")
conn.commit()


def add_user(user_id):
    try:
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except:
        pass


def get_all_users():
    c.execute("SELECT user_id FROM users")
    return c.fetchall()


def get_all_channels():
    c.execute("SELECT channel FROM channels")
    return [row[0] for row in c.fetchall()]


def add_channel(channel):
    try:
        c.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (channel,))
        conn.commit()
        return True
    except:
        return False


def remove_channel(channel):
    try:
        c.execute("DELETE FROM channels WHERE channel = ?", (channel,))
        conn.commit()
        return True
    except:
        return False


async def check_subscription(user_id, context):
    channels = get_all_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True


# ============== الأزرار الشفافة ==============
def get_inline_buttons():
    owner_username = os.getenv("OWNER_USERNAME", "sorx_baghdad")
    channel = CHANNEL_USERNAME.replace('@', '')
    
    keyboard = [
        [
            InlineKeyboardButton("👨‍💼 مطور البوت", url=f"https://t.me/{owner_username}"),
            InlineKeyboardButton("🏭 قناة المصنع", url=f"https://t.me/{channel}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_channel_buttons(channels):
    keyboard = []
    for channel in channels:
        ch = channel.replace('@', '')
        keyboard.append([InlineKeyboardButton(f"📢 {channel}", url=f"https://t.me/{ch}")])
    return InlineKeyboardMarkup(keyboard)


# ============== لوحة المطور ==============
async def show_panel(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📊 عدد المستخدمين"), KeyboardButton("📢 إذاعة")],
        [KeyboardButton("🔒 إدارة الاشتراك الإجباري")],
        [KeyboardButton("🗑️ تنظيف الملفات"), KeyboardButton("🔄 تحديث البوت")],
    ], resize_keyboard=True)

    await update.message.reply_text(
        f"⚙️ **لوحة تحكم المطور**\n\n"
        f"🔧 الإصدار: 9.0 (Cobalt API)\n"
        f"⚡ طريقة التحميل: Cobalt API\n"
        f"🗑️ التنظيف التلقائي: كل ساعة\n"
        f"📊 التقرير اليومي: منتصف الليل",
        reply_markup=keyboard
    )


# ============== أوامر البوت ==============
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    channels = get_all_channels()
    if channels:
        is_subscribed = await check_subscription(user_id, context)
        if not is_subscribed:
            keyboard = get_channel_buttons(channels)
            await update.message.reply_text(
                f"⚠️ **يرجى الاشتراك في القنوات التالية:**\n\n" +
                "\n".join([f"• {ch}" for ch in channels]) +
                f"\n\n✅ بعد الاشتراك، أعد إرسال /start",
                reply_markup=keyboard
            )
            return

    if user_id == OWNER_ID:
        await show_panel(update, context)
        return

    await update.message.reply_text(get_welcome(), reply_markup=get_inline_buttons())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **كيفية استخدام البوت:**\n\n"
        "1️⃣ انسخ رابط الفيديو أو الصورة\n"
        "2️⃣ ألصق الرابط في المحادثة\n"
        "3️⃣ انتظر حتى يتم التحميل\n\n"
        "✅ **يدعم:**\n"
        "• Instagram 📷\n"
        "• TikTok 🎵\n"
        "• YouTube ▶️\n"
        "• Facebook 📘\n"
        "• ومنصات أخرى كثيرة\n\n"
        "⚡ **تحميل سريع بدون علامات مائية**\n"
        "🗑️ **حذف تلقائي بعد الإرسال**\n\n"
        "⚡ **سورس بغداد** 🇮🇶",
        reply_markup=get_inline_buttons()
    )


# ============== تحميل المحتوى ==============
async def direct_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    channels = get_all_channels()
    if channels:
        is_subscribed = await check_subscription(user_id, context)
        if not is_subscribed:
            keyboard = get_channel_buttons(channels)
            await update.message.reply_text(
                f"⚠️ **يرجى الاشتراك في القنوات التالية:**\n\n" +
                "\n".join([f"• {ch}" for ch in channels]) +
                f"\n\n✅ بعد الاشتراك، أعد إرسال الرابط",
                reply_markup=keyboard
            )
            return

    url = update.message.text.strip()

    if not url.startswith(("http://", "https://")):
        await update.message.reply_text(get_invalid_url(), reply_markup=get_inline_buttons())
        return

    platform = detect_platform(url)
    status_msg = await update.message.reply_text(get_loading())

    file_path = None

    try:
        file_path = download_media(url, bot=context.bot, owner_id=OWNER_ID)

        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(get_error(), reply_markup=get_inline_buttons())
            return

        file_size = os.path.getsize(file_path) / (1024 * 1024)

        with open(file_path, "rb") as f:
            if file_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                await update.message.reply_photo(
                    photo=f,
                    caption=f"{get_success()}\n📌 {platform}\n🖼️ **صورة**\n💾 {file_size:.2f} MB",
                    reply_markup=get_inline_buttons()
                )
            else:
                await update.message.reply_video(
                    video=f,
                    caption=f"{get_success()}\n📌 {platform}\n🎬 **فيديو**\n💾 {file_size:.2f} MB",
                    reply_markup=get_inline_buttons()
                )

        await status_msg.delete()

        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ تم حذف الملف: {os.path.basename(file_path)}")

    except Exception as e:
        logger.error(f"خطأ: {e}")
        await status_msg.edit_text(get_error(), reply_markup=get_inline_buttons())
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


# ============== معالج الرسائل ==============
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if update.message and update.message.text:
        text = update.message.text.strip()

        # ====== أوامر المطور ======
        if user_id == OWNER_ID:
            if text == "📊 عدد المستخدمين":
                c.execute("SELECT COUNT(*) FROM users")
                total = c.fetchone()[0]
                await update.message.reply_text(f"📊 **عدد المستخدمين:** {total}")
                return

            elif text == "📢 إذاعة":
                await update.message.reply_text("✉️ أرسل رسالة الإذاعة للمستخدمين:")
                context.user_data["awaiting_broadcast"] = True
                return

            elif text == "🗑️ تنظيف الملفات":
                deleted = clean_old_files()
                await update.message.reply_text(f"✅ تم حذف {deleted} ملف قديم")
                return

            elif text == "🔄 تحديث البوت":
                await update.message.reply_text("🔄 جاري تحديث البوت...")
                success, message = update_ytdlp()
                if success:
                    await update.message.reply_text(message)
                    # إشعار للمطور
                    from messages import get_dev_message
                    msg = get_dev_message("update_success", time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id=OWNER_ID)
                    await context.bot.send_message(chat_id=OWNER_ID, text=msg, parse_mode="Markdown")
                else:
                    await update.message.reply_text(message)
                return

            elif text == "🔒 إدارة الاشتراك الإجباري":
                keyboard = ReplyKeyboardMarkup([
                    [KeyboardButton("➕ إضافة قناة"), KeyboardButton("❌ حذف قناة")],
                    [KeyboardButton("📋 عرض القنوات"), KeyboardButton("🔙 رجوع")]
                ], resize_keyboard=True)
                await update.message.reply_text("🔒 **إدارة الاشتراك الإجباري**", reply_markup=keyboard)
                return

            elif text == "➕ إضافة قناة":
                await update.message.reply_text("📝 أرسل معرف القناة (مثال: @channel_username)")
                context.user_data["awaiting_channel_add"] = True
                return

            elif text == "❌ حذف قناة":
                channels = get_all_channels()
                if not channels:
                    await update.message.reply_text("❌ لا توجد قنوات")
                    return
                keyboard = ReplyKeyboardMarkup(
                    [[KeyboardButton(ch)] for ch in channels] + [[KeyboardButton("🔙 رجوع")]],
                    resize_keyboard=True
                )
                await update.message.reply_text("📌 اختر قناة للحذف:", reply_markup=keyboard)
                context.user_data["awaiting_channel_delete"] = True
                return

            elif text == "📋 عرض القنوات":
                channels = get_all_channels()
                if channels:
                    await update.message.reply_text("📋 **القنوات:**\n" + "\n".join([f"• {ch}" for ch in channels]))
                else:
                    await update.message.reply_text("❌ لا توجد قنوات")
                return

            elif text == "🔙 رجوع":
                await show_panel(update, context)
                return

            # ====== معالجة الإذاعة ======
            if context.user_data.get("awaiting_broadcast"):
                msg_text = text
                context.user_data["awaiting_broadcast"] = False
                users = get_all_users()
                status = await update.message.reply_text(f"⏳ جاري الإذاعة لـ {len(users)} مستخدم...")
                count = 0
                for user in users:
                    try:
                        await context.bot.send_message(chat_id=user[0], text=msg_text)
                        count += 1
                        await asyncio.sleep(0.05)
                    except:
                        continue
                await status.edit_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم")
                return

            # ====== معالجة إضافة قناة ======
            if context.user_data.get("awaiting_channel_add"):
                channel = text
                if add_channel(channel):
                    await update.message.reply_text(f"✅ تم إضافة {channel}")
                else:
                    await update.message.reply_text("❌ فشل الإضافة")
                context.user_data["awaiting_channel_add"] = False
                await show_panel(update, context)
                return

            # ====== معالجة حذف قناة ======
            if context.user_data.get("awaiting_channel_delete"):
                channel = text
                if channel == "🔙 رجوع":
                    context.user_data["awaiting_channel_delete"] = False
                    await show_panel(update, context)
                    return
                if remove_channel(channel):
                    await update.message.reply_text(f"✅ تم حذف {channel}")
                else:
                    await update.message.reply_text("❌ فشل الحذف")
                context.user_data["awaiting_channel_delete"] = False
                await show_panel(update, context)
                return

        # ====== تحميل (لجميع المستخدمين) ======
        if text.startswith(("http://", "https://")):
            await direct_download(update, context)
            return
        else:
            if user_id != OWNER_ID:
                await update.message.reply_text(
                    "📌 أرسل رابط فيديو أو صورة للتحميل",
                    reply_markup=get_inline_buttons()
                )


# ============== معالج الأخطاء ==============
async def error_handler(update, context):
    logger.error(f"خطأ: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ حدث خطأ غير متوقع")


def close_browsers():
    logger.info("✅ لا يوجد متصفح مفتوح")


atexit.register(close_browsers)


# ============== التشغيل الرئيسي ==============
def main():
    print("\n" + "="*60)
    print("🤖 **بوت سورس بغداد - النسخة النهائية**")
    print("="*60)
    print(f"⚡ طريقة التحميل: Cobalt API")
    print(f"🔄 تحديث البوت: تلقائي عند بدء التشغيل")
    print(f"📊 تقرير يومي: منتصف الليل")
    print("="*60 + "\n")

    auto_update()
    print()   
    
    os.makedirs("downloads", exist_ok=True)
    clean_old_files()
    start_cleanup_scheduler()

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)  # <--- أضف هذا السطر فقط
        .build()
    )

    start_daily_report_scheduler(application.bot)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_error_handler(error_handler)

    print("🚀 البوت جاهز للتشغيل...")
    print("📨 سيتم إرسال إشعارات للمطور عند الحاجة")
    print("📊 تقرير يومي في منتصف الليل")
    print("="*60 + "\n")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ: {e}")


if __name__ == "__main__":
    main()
