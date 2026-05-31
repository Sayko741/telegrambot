#!/usr/bin/env python3
"""
Telegram Multi-Platform Downloader Bot
Compatible with Python 3.13, Railway, yt-dlp
"""

import os
import re
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
ADMIN_ID = os.environ.get("ADMIN_ID")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ==================== STATE MANAGEMENT ====================
class UserState:
    def __init__(self):
        self.language: str | None = None
        self.platform: str | None = None
        self.current_link: str | None = None
        self.search_results: list = []
        self.current_video_id: str | None = None
        self.current_action: str | None = None
        self.menu_state: str | None = None


user_states: dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]


# ==================== KEYBOARDS ====================
def get_main_keyboard(lang: str = "en") -> ReplyKeyboardMarkup:
    labels = {
        "ar": {"start": "🏠 الرئيسية", "language": "🌐 اللغة", "help": "❓ مساعدة"},
        "en": {"start": "🏠 Start", "language": "🌐 Language", "help": "❓ Help"},
    }
    keyboard = [
        [labels[lang]["start"]],
        [labels[lang]["language"]],
        [labels[lang]["help"]],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_language_keyboard() -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ]


def get_platform_keyboard(lang: str) -> list[list[InlineKeyboardButton]]:
    labels = MESSAGES[lang]
    back_label = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    return [
        [InlineKeyboardButton(labels["youtube"], callback_data="platform_youtube")],
        [InlineKeyboardButton(labels["tiktok"], callback_data="platform_tiktok")],
        [InlineKeyboardButton(labels["facebook"], callback_data="platform_facebook")],
        [InlineKeyboardButton(labels["instagram"], callback_data="platform_instagram")],
        [InlineKeyboardButton(back_label, callback_data="back")],
    ]


def get_action_keyboard(lang: str, platform: str) -> list[list[InlineKeyboardButton]]:
    msg = MESSAGES[lang]
    back_label = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    if platform == "youtube":
        return [
            [InlineKeyboardButton("🔍 " + msg["search"], callback_data="action_search"),
             InlineKeyboardButton("🔗 " + msg["send_link"], callback_data="action_link")],
            [InlineKeyboardButton(back_label, callback_data="back_platform")],
        ]
    else:
        return [
            [InlineKeyboardButton("🔗 " + msg["send_link"], callback_data="action_link")],
            [InlineKeyboardButton(back_label, callback_data="back_platform")],
        ]


def get_quality_keyboard(lang: str) -> list[list[InlineKeyboardButton]]:
    back_label = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    if lang == "ar":
        return [
            [InlineKeyboardButton("📺 144p", callback_data="q_144"),
             InlineKeyboardButton("📺 240p", callback_data="q_240"),
             InlineKeyboardButton("📺 360p", callback_data="q_360")],
            [InlineKeyboardButton("📺 480p", callback_data="q_480"),
             InlineKeyboardButton("📺 720p", callback_data="q_720"),
             InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
            [InlineKeyboardButton("🎵 تحويل إلى MP3", callback_data="convert_mp3")],
            [InlineKeyboardButton(back_label, callback_data="back")],
        ]
    else:
        return [
            [InlineKeyboardButton("📺 144p", callback_data="q_144"),
             InlineKeyboardButton("📺 240p", callback_data="q_240"),
             InlineKeyboardButton("📺 360p", callback_data="q_360")],
            [InlineKeyboardButton("📺 480p", callback_data="q_480"),
             InlineKeyboardButton("📺 720p", callback_data="q_720"),
             InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
            [InlineKeyboardButton("🎵 Convert to MP3", callback_data="convert_mp3")],
            [InlineKeyboardButton(back_label, callback_data="back")],
        ]


# ==================== MESSAGES ====================
MESSAGES = {
    "ar": {
        "welcome": "مرحباً! اختر اللغة للمتابعة:",
        "language_selected": "✅ تم اختيار اللغة: العربية",
        "choose_platform": "📌 اختر المنصة:",
        "search_or_link": "📎 أرسل رابطًا للتحميل، أو ابحث بدون رابط.",
        "send_link": "🔗 أرسل رابط",
        "search": "🔍 بحث",
        "search_query": "📝 أدخل كلمة البحث:",
        "enter_link": "🔗 أدخل الرابط للتحميل:",
        "select_quality": "🎬 اختر الجودة:",
        "downloading": "⏳ جاري التحميل...",
        "converting": "⏳ جاري التحويل إلى MP3...",
        "no_results": "❌ لم يتم العثور على نتائج",
        "error": "❌ حدث خطأ. يرجى المحاولة مرة أخرى.",
        "success": "✅ تم التحميل بنجاح!",
        "back": "⬅️Back رجوع",
        "help_title": "❓ مساعدة",
        "help_text": """📌 دليل الاستخدام:

1️⃣ اختر اللغة
2️⃣ اختر منصة
3️⃣ أرسل رابط أو ابحث
4️⃣ اختر الجودة أو حول لـ MP3

📧 للتواصل: mohamedeslammaklad700@gmail.com""",
        "youtube": "▶️ يوتيوب",
        "tiktok": "🎵 تيك توك",
        "facebook": "📘 فيسبوك",
        "instagram": "📸 انستغرام",
    },
    "en": {
        "welcome": "Hello! Choose your language to continue:",
        "language_selected": "✅ Language selected: English",
        "choose_platform": "📌 Choose platform:",
        "search_or_link": "📎 Send a link to download, or search without a link.",
        "send_link": "🔗 Send link",
        "search": "🔍 Search",
        "search_query": "📝 Enter search query:",
        "enter_link": "🔗 Enter link to download:",
        "select_quality": "🎬 Select quality:",
        "downloading": "⏳ Downloading...",
        "converting": "⏳ Converting to MP3...",
        "no_results": "❌ No results found",
        "error": "❌ An error occurred. Please try again.",
        "success": "✅ Downloaded successfully!",
        "back": "⬅️ Back",
        "help_title": "❓ Help",
        "help_text": """📌 How to use:

1️⃣ Choose language
2️⃣ Choose platform
3️⃣ Send link or search
4️⃣ Select quality or convert to MP3

📧 Contact: mohamedeslammaklad700@gmail.com""",
        "youtube": "▶️ YouTube",
        "tiktok": "🎵 TikTok",
        "facebook": "📘 Facebook",
        "instagram": "📸 Instagram",
    },
}


# ==================== YOUTUBE FUNCTIONS ====================
async def youtube_search(query: str, max_results: int = 10) -> list[dict]:
    if not YOUTUBE_API_KEY:
        return []
    
    import aiohttp
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    for item in data.get("items", []):
                        results.append({
                            "title": item["snippet"]["title"],
                            "channel": item["snippet"]["channelTitle"],
                            "video_id": item["id"]["videoId"],
                            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                        })
                    return results
                return []
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return []


def parse_duration(duration: str) -> str:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    return "0:00"


def format_views(views: str) -> str:
    try:
        v = int(views)
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        elif v >= 1_000:
            return f"{v/1_000:.1f}K"
        return str(v)
    except:
        return views


# ==================== DOWNLOAD FUNCTION ====================
async def download_video(url: str, quality: str = "720p", convert_mp3: bool = False) -> str | None:
    import yt_dlp

    download_dir = "/tmp"
    os.makedirs(download_dir, exist_ok=True)

    try:
        if convert_mp3:
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        else:
            height = int(quality[:-1])
            ydl_opts = {
                "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
            }

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, url)
            if info is None:
                return None
            filename = ydl.prepare_filename(info)

            if convert_mp3:
                filename = filename.rsplit(".", 1)[0] + ".mp3"

            return filename
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None


# ==================== HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    if state.language is None:
        keyboard = InlineKeyboardMarkup(get_language_keyboard())
        await update.message.reply_text(MESSAGES["ar"]["welcome"], reply_markup=keyboard)
    else:
        lang = state.language
        keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang))
        await update.message.reply_text(MESSAGES[lang]["choose_platform"], reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    await update.message.reply_text(MESSAGES[lang]["help_text"])


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup(get_language_keyboard())
    await update.message.reply_text("اختر اللغة:" if get_user_state(update.effective_user.id).language == "ar" else "Select language:", reply_markup=keyboard)


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang_code = query.data.split("_")[1]
    state.language = lang_code

    await query.edit_message_text(MESSAGES[lang_code]["language_selected"])
    keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang_code))
    await query.message.reply_text(MESSAGES[lang_code]["choose_platform"], reply_markup=keyboard)


async def platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"

    if query.data == "back":
        state.menu_state = None
        state.platform = None
        keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang))
        await query.edit_message_text(MESSAGES[lang]["choose_platform"], reply_markup=keyboard)
        return

    platform = query.data.split("_")[1]
    state.platform = platform

    keyboard = InlineKeyboardMarkup(get_action_keyboard(lang, platform))
    await query.edit_message_text(MESSAGES[lang]["search_or_link"], reply_markup=keyboard)


async def back_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"

    keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang))
    await query.edit_message_text(MESSAGES[lang]["choose_platform"], reply_markup=keyboard)


async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"

    if query.data == "back_platform":
        keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang))
        await query.edit_message_text(MESSAGES[lang]["choose_platform"], reply_markup=keyboard)
        return

    action = query.data.split("_")[1]
    state.current_action = action

    msg = MESSAGES[lang]
    if action == "search":
        await query.edit_message_text(msg["search_query"])
    else:
