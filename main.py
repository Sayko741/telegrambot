#!/usr/bin/env python3
"""Telegram Bot - Python 3.13, Railway, yt-dlp"""

import os, re, asyncio, logging, aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
ADMIN_ID = os.environ.get("ADMIN_ID")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== STATE ====================
class UserState:
    def __init__(self):
        self.language = None
        self.platform = None
        self.current_link = None
        self.search_results = []
        self.current_video_id = None
        self.current_action = None

user_states = {}

def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]

# ==================== MESSAGES ====================
MESSAGES = {
    "ar": {
        "welcome": "مرحباً! اختر اللغة:", "language_selected": "✅ تم اختيار العربية",
        "choose_platform": "📌 اختر المنصة:", "search_or_link": "أرسل رابطاً أو ابحث بدون رابط",
        "send_link": "🔗 أرسل رابط", "search": "🔍 بحث", "search_query": "📝 أدخل كلمة البحث:",
        "select_quality": "🎬 اختر الجودة:", "downloading": "⏳ جاري التحميل...",
        "converting": "⏳ جاري التحويل...", "no_results": "❌ لا توجد نتائج", "error": "❌ خطأ",
        "help_text": "📌 طريقة الاستخدام:\n1️⃣ اختر اللغة\n2️⃣ اختر المنصة\n3️⃣ أرسل رابط أو ابحث\n4️⃣ اختر الجودة\n\n📧 للتواصل: mohamedeslammaklad700@gmail.com",
        "youtube": "▶️ يوتيوب", "tiktok": "🎵 تيك توك", "facebook": "📘 فيسبوك", "instagram": "📸 انستغرام",
    },
    "en": {
        "welcome": "Hello! Choose language:", "language_selected": "✅ English selected",
        "choose_platform": "📌 Choose platform:", "search_or_link": "Send link or search without link",
        "send_link": "🔗 Send link", "search": "🔍 Search", "search_query": "📝 Enter search query:",
        "select_quality": "🎬 Select quality:", "downloading": "⏳ Downloading...",
        "converting": "⏳ Converting...", "no_results": "❌ No results", "error": "❌ Error",
        "help_text": "📌 How to use:\n1️⃣ Choose language\n2️⃣ Choose platform\n3️⃣ Send link or search\n4️⃣ Select quality\n\n📧 Contact: mohamedeslammaklad700@gmail.com",
        "youtube": "▶️ YouTube", "tiktok": "🎵 TikTok", "facebook": "📘 Facebook", "instagram": "📸 Instagram",
    }
}

# ==================== KEYBOARDS ====================
def kb_lang():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"), InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]])

def kb_platform(lang):
    msg = MESSAGES[lang]
    back = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(msg["youtube"], callback_data="platform_youtube")],
        [InlineKeyboardButton(msg["tiktok"], callback_data="platform_tiktok")],
        [InlineKeyboardButton(msg["facebook"], callback_data="platform_facebook")],
        [InlineKeyboardButton(msg["instagram"], callback_data="platform_instagram")],
        [InlineKeyboardButton(back, callback_data="back")]
    ])

def kb_action(lang, platform):
    msg = MESSAGES[lang]
    back = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    if platform == "youtube":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 " + msg["search"], callback_data="action_search"),
             InlineKeyboardButton("🔗 " + msg["send_link"], callback_data="action_link")],
            [InlineKeyboardButton(back, callback_data="back_platform")]
        ])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔗 " + msg["send_link"], callback_data="action_link")], [InlineKeyboardButton(back, callback_data="back_platform")]])

def kb_quality(lang):
    back = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📺 144p", callback_data="q_144"), InlineKeyboardButton("📺 240p", callback_data="q_240"), InlineKeyboardButton("📺 360p", callback_data="q_360")],
            [InlineKeyboardButton("📺 480p", callback_data="q_480"), InlineKeyboardButton("📺 720p", callback_data="q_720"), InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
            [InlineKeyboardButton("🎵 تحويل MP3", callback_data="convert_mp3")],
            [InlineKeyboardButton(back, callback_data="back")]
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 144p", callback_data="q_144"), InlineKeyboardButton("📺 240p", callback_data="q_240"), InlineKeyboardButton("📺 360p", callback_data="q_360")],
        [InlineKeyboardButton("📺 480p", callback_data="q_480"), InlineKeyboardButton("📺 720p", callback_data="q_720"), InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 Convert MP3", callback_data="convert_mp3")],
        [InlineKeyboardButton(back, callback_data="back")]
    ])

# ==================== YOUTUBE SEARCH ====================
async def youtube_search(query, max_results=10):
    if not YOUTUBE_API_KEY:
        return []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "key": YOUTUBE_API_KEY}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [{"title": i["snippet"]["title"], "channel": i["snippet"]["channelTitle"], "video_id": i["id"]["videoId"]} for i in data.get("items", [])]
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
    return []

# ==================== DOWNLOAD ====================
async def download_video(url, quality="720p", convert_mp3=False):
    import yt_dlp
    download_dir = "/tmp"
    os.makedirs(download_dir, exist_ok=True)
    try:
        ydl_opts = {
            "format": "bestaudio" if convert_mp3 else f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]",
            "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }
        if convert_mp3:
            ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        
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
            return filename.rsplit(".", 1)[0] + ".mp3" if convert_mp3 else filename
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

# ==================== HANDLERS ====================
async def start_command(update, context):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    if state.language is None:
        await update.message.reply_text(MESSAGES["ar"]["welcome"], reply_markup=kb_lang())
    else:
        await update.message.reply_text(MESSAGES[state.language]["choose_platform"], reply_markup=kb_platform(state.language))

async def help_command(update, context):
    lang = get_user_state(update.effective_user.id).language or "en"
    await update.message.reply_text(MESSAGES[lang]["help_text"])

async def language_command(update, context):
    await update.message.reply_text("اختر اللغة:" if get_user_state(update.effective_user.id).language == "ar" else "Select language:", reply_markup=kb_lang())

async def lang_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang_code = query.data.split("_")[1]
    state.language = lang_code
    await query.edit_message_text(MESSAGES[lang_code]["language_selected"])
    await query.message.reply_text(MESSAGES[lang_code]["choose_platform"], reply_markup=kb_platform(lang_code))

async def platform_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    
    if query.data == "back":
        state.platform = None
        await query.edit_message_text(MESSAGES[lang]["choose_platform"], reply_markup=kb_platform(lang))
        return
    
    platform = query.data.split("_")[1]
    state.platform = platform
    await query.edit_message_text(MESSAGES[lang]["search_or_link"], reply_markup=kb_action(lang, platform))

async def action_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    
    if query.data == "back_platform":
        await query.edit_message_text(MESSAGES[lang]["choose_platform"], reply_markup=kb_platform(lang))
        return
    
    action = query.data.split("_")[1]
    state.current_action = action
    
    if action == "search":
        await query.edit_message_text(msg["search_query"])
    else:
        await query.edit_message_text(msg.get("enter_link", "Send link:"))

async def quality_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    
    if query.data == "back":
        state.current_link = None
        state.current_video_id = None
        await query.edit_message_text(MESSAGES[lang]["search_or_link"], reply_markup=kb_action(lang, state.platform))
        return
    
    is_mp3 = query.data == "convert_mp3"
    quality = "720p"
    if not is_mp3:
        quality = query.data.replace("q_", "") + "p"
    
    await query.edit_message_text(msg["converting"] if is_mp3 else msg["downloading"])
    
    # Get URL and download
    url = state.current_link or (f"https://youtube.com/watch?v={state.current_video_id}" if state.current_video_id else None)
    if url:
        filename = await download_video(url, quality, is_mp3)
        if filename and os.path.exists(filename):
            await query.message.reply_video(open(filename, "rb"))
            os.remove(filename)
        else:
            await query.message.reply_text(msg["error"])

async def handle_message(update, context):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    text = update.message.text
    
    is_link = any(x in text.lower() for x in ["http", "www.", ".com", ".be", ".to/", "fb.watch", "youtu.be"])
    
    if is_link:
        state.current_link = text
        if "youtube" in text or "youtu.be" in text:
            state.platform = "youtube"
        elif "tiktok" in text:
            state.platform = "tiktok"
        elif "facebook" in text or "fb.watch" in text:
            state.platform = "facebook"
        elif "instagram" in text:
            state.platform = "instagram"
        
        await update.message.reply_text(msg["select_quality"], reply_markup=kb_quality(lang))
    
    elif state.platform == "youtube" and state.current_action == "search":
        await update.message.reply_text("⏳ " + msg.get("search", "Searching") + "...")
        results = await youtube_search(text)
        state.search_results = results
        
        if not results:
            await update.message.reply_text(msg["no_results"])
            return
        
        response = f'📋┃Search results for "{text}"\n\n'
        for v in results[:5]:
            response += f"🎬 {v['title']}\n👤 {v['channel']}\n🔗 /dl_{v['video_id']}\n\n"
        
        buttons = [[InlineKeyboardButton(f"▶️ {v['title'][:30]}...", callback_data=f"video_{v['video_id']}")] for v in results[:5]]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(buttons))

async def video_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    
    video_id = query.data.replace("video_", "")
    state.current_video_id = video_id
    
    await query.edit_message_text(MESSAGES[lang]["select_quality"], reply_markup=kb_quality(lang))

async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(platform_callback, pattern="^platform_"))
    app.add_handler(CallbackQueryHandler(action_callback, pattern="^action_"))
    app.add_handler(CallbackQueryHandler(quality_callback, pattern="^(q_|convert_|back$)"))
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^video_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
