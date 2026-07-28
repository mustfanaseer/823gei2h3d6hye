import random

# ============== رسائل المستخدمين ==============

WELCOME_MESSAGES = [
    "👑 **أهلاً بك في بوت التحميل!** 🚀\n\n"
    "📥 أرسل رابط فيديو أو صورة وسأقوم بتحميلها لك فوراً.\n\n"
    "✅ **يدعم:**\n"
    "• Instagram 📷\n"
    "• TikTok 🎵\n"
    "• YouTube ▶️\n"
    "• Facebook 📘\n"
    "• ومنصات أخرى كثيرة\n\n"
    "⚡ **تحميل سريع بدون علامات مائية**\n"
    "🗑️ يتم حذف الملفات بعد الإرسال تلقائياً"
]

SUCCESS_MESSAGES = [
    "✅ **تم التحميل بنجاح!** 🎉",
    "📥 **المحتوى جاهز!** استلمه الآن 📦",
    "🚀 **اكتمل التحميل!** جودة عالية ⚡",
    "🎬 **تم تجهيز الملف!** استمتع 📺"
]

ERROR_MESSAGES = [
    "❌ **عذراً! حدث خطأ أثناء التحميل.**\n💡 يرجى التأكد من الرابط والمحاولة مرة أخرى.",
    "⚠️ **الرابط غير صحيح!**\n📌 يرجى إرسال رابط صحيح.",
    "❌ **تعذر تحميل المحتوى!**\n💡 حاول مرة أخرى بعد قليل."
]

PRIVACY_MESSAGE = "🔒 **هذا المحتوى خاص** ولا يمكن تحميله."
LOADING_MESSAGE = "⏳ جاري تحميل المحتوى... يرجى الانتظار ⏳"
INVALID_URL_MESSAGE = "❌ **الرابط غير صحيح!**\n📌 يرجى إرسال رابط يبدأ بـ http:// أو https://"

# ============== رسائل المطور ==============

DEV_MESSAGES = {
    "update_success": (
        "✅ **تم تحديث البوت بنجاح!**\n\n"
        "🕐 **وقت التحديث:** {time}\n"
        "🔐 **البوت جاهز للعمل**\n"
        "🆔 **معرف المستخدم:** {user_id}"
    ),
    "download_failed": (
        "❌ **فشل تحميل المحتوى!**\n\n"
        "📌 **المنصة:** {platform}\n"
        "🔄 **تمت المحاولة عبر:** Cobalt API\n"
        "💡 **السبب:** قد يكون الرابط غير صحيح أو المحتوى غير متاح\n"
        "🆔 **معرف المستخدم:** {user_id}"
    ),
    "daily_report": (
        "📊 **تقرير أداء البوت اليومي**\n\n"
        "📅 **التاريخ:** {date}\n"
        "✅ **التحميلات الناجحة:** {success_count}\n"
        "❌ **التحميلات الفاشلة:** {fail_count}\n"
        "💾 **المساحة المستخدمة:** {used_space} MB\n"
        "📁 **الملفات المؤقتة:** {temp_files}\n"
        "🆔 **معرف المستخدم:** {user_id}"
    ),
    "bot_started": (
        "🤖 **تم تشغيل البوت بنجاح!**\n\n"
        "⚡ **طريقة التحميل:** Cobalt API\n"
        "🕐 **وقت التشغيل:** {time}\n"
        "🔐 **جميع الأنظمة جاهزة**\n"
        "🆔 **معرف المستخدم:** {user_id}"
    )
}

# ============== دوال الحصول على الرسائل ==============

def get_welcome():
    return random.choice(WELCOME_MESSAGES)

def get_success():
    return random.choice(SUCCESS_MESSAGES)

def get_error():
    return random.choice(ERROR_MESSAGES)

def get_privacy():
    return PRIVACY_MESSAGE

def get_loading():
    return LOADING_MESSAGE

def get_invalid_url():
    return INVALID_URL_MESSAGE

def get_dev_message(key, **kwargs):
    msg = DEV_MESSAGES.get(key, "")
    if kwargs:
        try:
            return msg.format(**kwargs)
        except:
            return msg
    return msg