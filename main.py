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
        self.menu_state: str | None = None  # For back navigation


user_states: dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]


# ==================== REPLY KEYBOARD ====================
def get_main_keyboard(lang: str = "en") -> ReplyKeyboardMarkup:
    """Main keyboard with Start, Language, Help buttons"""
    labels = {
        "ar": {"start": "🏠 الرئيسية", "language": "🌐 اللغة", "help": "❓ помощь"},
        "en": {"start": "🏠 Start", "language": "🌐 Language", "help": "❓ Help"},
    }
    
    keyboard = [
        [labels[lang]["start"]],
        [labels[lang]["language"]],
        [labels[lang]["help"]],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ==================== MESSAGES ====================
MESSAGES = {
    "ar": {
        "welcome": "مرحباً! أنا بوت تحميل الوسائط المتعددة.\nاختر اللغة للمتابعة:",
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
        "help_title": "❓ pomocь использовать Bot",
        "help_text": """📌 دليل الاستخدام:

1️⃣ اختر اللغة المفضلة
2️⃣ اختر منصة (يوتيوب، تيك توك، فيسبوك، انستغرام)
3️⃣ اختر: أرسل رابط أو ابحث (لليوتيوب فقط)
4️⃣ اختر جودة الفيديو أو تحويل إلى MP3
5️⃣ سيتم تحميل الملف وإرساله لك

💡 نصائح:
- يدعم الفيديوهات حتى 1080p
- يمكن تحويل أي فيديو إلى MP3
- للبحث اكتب كلمة البحث فقط

📧 для связи: mohamedeslammaklad700@gmail.com""",
        "youtube": "▶️ يوتيوب",
        "tiktok": "🎵 تيك توك",
        "facebook": "📘 فيسبوك",
        "instagram": "📸 انستغرام",
    },
    "en": {
        "welcome": "Hello! I'm a multimedia downloader bot.\nChoose your language to continue:",
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

1️⃣ Choose your preferred language
2️⃣ Choose platform (YouTube, TikTok, Facebook, Instagram)
3️⃣ Choose: Send link or Search (YouTube only)
4️⃣ Select video quality or convert to MP3
5️⃣ The file will be downloaded and sent to you

💡 Tips:
- Supports videos up to 1080p
- Can convert any video to MP3
- To search, just type your search query

📧 Contact: mohamedeslammaklad700@gmail.com""",
        "youtube": "▶️ YouTube",
        "tiktok": "🎵 TikTok",
        "facebook": "📘 Facebook",
        "instagram": "📸 Instagram",
    },
}

# ==================== BACK KEYBOARDS ====================
def get_back_keyboard(lang: str) -> list[list[InlineKeyboardButton]]:
    """Back button keyboard"""
    label = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    return [[InlineKeyboardButton(label, callback_data="back")]]


# ==================== QUALITY KEYBOARDS ====================
def get_quality_keyboard(lang: str) -> list[list[InlineKeyboardButton]]:
    """Quality selection keyboard"""
    if lang == "ar":
        return [
            [InlineKeyboardButton("📺 144p", callback_data="q_144"),
             InlineKeyboardButton("📺 240p", callback_data="q_240"),
             InlineKeyboardButton("📺 360p", callback_data="q_360")],
            [InlineKeyboardButton("📺 480p", callback_data="q_480"),
             InlineKeyboardButton("📺 720p", callback_data="q_720"),
             InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
            [InlineKeyboardButton("🎵 تحويل إلى MP3", callback_data="convert_mp3")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back")],
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
            [InlineKeyboardButton("⬅️ Back", callback_data="back")],
        ]


def get_platform_keyboard(lang: str) -> list[list[InlineKeyboardButton]]:
    """Platform selection keyboard"""
    labels = MESSAGES[lang]
    return [
        [InlineKeyboardButton(labels["youtube"], callback_data="platform_youtube")],
        [InlineKeyboardButton(labels["tiktok"], callback_data="platform_tiktok")],
        [InlineKeyboardButton(labels["facebook"], callback_data="platform_facebook")],
        [InlineKeyboardButton(labels["instagram"], callback_data="platform_instagram")],
        [InlineKeyboardButton("⬅️ " + ("رجوع" if lang == "ar" else "Back"), callback_data="back")],
    ]


def get_action_keyboard(lang: str, platform: str) -> list[list[InlineKeyboardButton]]:
    """Search/Link action keyboard"""
    msg = MESSAGES[lang]
    if platform == "youtube":
        return [
            [InlineKeyboardButton("🔍 " + msg["search"], callback_data="action_search"),
             InlineKeyboardButton("🔗 " + msg["send_link"], callback_data="action_link")],
            [InlineKeyboardButton("⬅️ " + ("رجوع" if lang == "ar" else "Back"), callback_data="back_platform")],
        ]
    else:
        return [
            [InlineKeyboardButton("🔗 " + msg["send_link"], callback_data="action_link")],
            [InlineKeyboardButton("⬅️ " + ("رجوع" if lang == "ar" else "Back"), callback_data="back_platform")],
        ]


def get_language_keyboard() -> list[list[InlineKeyboardButton]]:
    """Language selection keyboard"""
    return [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ]


# ==================== YOUTUBE SEARCH ====================
async def youtube_search(query: str, max_results: int = 10) -> list[dict]:
    """Search YouTube using Data API v3"""
    import aiohttp

    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not set")
        return []

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
                else:
                    logger.error(f"YouTube API error: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return []


async def get_video_details(video_id: str) -> dict | None:
    """Get video duration and view count"""
    import aiohttp

    if not YOUTUBE_API_KEY:
        return None

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "contentDetails,statistics",
        "id": video_id,
        "key": YOUTUBE_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["items"]:
                        item = data["items"][0]
                        duration = item["contentDetails"]["duration"]
                        views = item["statistics"].get("viewCount", "0")
                        return {
                            "duration": parse_duration(duration),
                            "views": format_views(views),
                        }
                return None
    except Exception as e:
        logger.error(f"Video details error: {e}")
        return None


def parse_duration(duration: str) -> str:
    """Parse ISO 8601 duration to readable format"""
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
    """Format views count"""
    try:
        v = int(views)
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        elif v >= 1_000:
            return f"{v/1_000:.1f}K"
        else:
            return str(v)
    except:
        return views


# ==================== DOWNLOAD FUNCTIONS ====================
async def download_video(
    url: str, quality: str = "720p", convert_mp3: bool = False
) -> str | None:
    """Download video using yt-dlp"""
    import yt_dlp

    download_dir = "/tmp"
    os.makedirs(download_dir, exist_ok=True)

    if convert_mp3:
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
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


# ==================== TELEGRAM HANDLERS ====================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    # Check if user already has a language set
    if state.language is None:
        # Show language selection
        keyboard = InlineKeyboardMarkup(get_language_keyboard())
        await update.message.reply_text(
            MESSAGES["ar"]["welcome"],
            reply_markup=keyboard,
        )
    else:
        lang = state.language
        msg = MESSAGES[lang]
        
        # Show platform selection
        keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang))
        await update.message.reply_text(
            msg["choose_platform"],
            reply_markup=keyboard,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    
    msg = MESSAGES[lang]
    keyboard = ReplyKeyboardMarkup(
        [["⬅️ " + ("رجوع" if lang == "ar" else "Back")]],
        resize_keyboard=True,
    )
    
    await update.message.reply_text(
        msg["help_text"],
        reply_markup=keyboard,
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language command - change language"""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    
    keyboard = InlineKeyboardMarkup(get_language_keyboard())
    
    # Get current language or default
    current = state.language or "en"
    text = "اختر اللغة:" if current == "ar" else "Select language:"
    
    await update.message.reply_text(text, reply_markup=keyboard)


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline language selection"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = get_user_state(user_id)

    lang_code = query.data.split("_")[1]
    state.language = lang_code
    msg = MESSAGES[lang_code]

    # Confirm language and show platform
    await query.edit_message_text(msg["language_selected"])
    
    # Show platform selection with main keyboard
    keyboard = InlineKeyboardMarkup(get_platform_keyboard(lang_code))
    await query.message.reply_text(
        msg["choose_platform"],
        reply_markup=keyboard,
    )


async def platform_callback(update:
