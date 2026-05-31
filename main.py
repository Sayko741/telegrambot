#!/usr/bin/env python3
"""Telegram Bot - Auto detect platform, search, download"""

import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
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

user_states = {}

def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]

# ==================== MESSAGES ====================
MESSAGES = {
    "ar": {
        "welcome": "مرحباً! اختر لغتك:", "language_selected": "✅ تم اختيار العربية",
        "main_menu": "📎 أرسل رابطاً للتحميل، أو ابحث بدون رابط:",
        "send_link": "🔗 أرسل رابط", "search": "🔍 بحث", "search_query": "📝 أدخل اسم الفيديو:",
        "select_quality": "🎬 اختر الجودة:", "downloading": "⏳ جاري التحميل...",
        "converting": "⏳ جاري التحويل...", "no_results": "❌ لا توجد نتائج", "error": "❌ حدث خطأ",
        "success": "✅ تم التحميل بنجاح!",
        "help_text": "📌 طريقة الاستخدام:\n1️⃣ اختر لغتك\n2️⃣ أرسل رابط أو ابحث\n3️⃣ اختر الجودة\n4️⃣ سيتم الإرسال\n\n📧 للتواصل: mohamedeslammaklad700@gmail.com",
    },
    "en": {
        "welcome": "Hello! Choose language:", "language_selected": "✅ English selected",
        "main_menu": "📎 Send link to download, or search:",
        "send_link": "🔗 Send link", "search": "🔍 Search", "search_query": "📝 Enter video name:",
        "select_quality": "🎬 Select quality:", "downloading": "⏳ Downloading...",
        "converting": "⏳ Converting...", "no_results": "❌ No results", "error": "❌ Error",
        "success": "✅ Downloaded successfully!",
        "help_text": "📌 How to use:\n1️⃣ Choose language\n2️⃣ Send link or search\n3️⃣ Select quality\n4️⃣ File will be sent\n\n📧 Contact: mohamedeslammaklad700@gmail.com",
    }
}

# ==================== KEYBOARDS ====================
def kb_lang():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    ]])

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

# ==================== DETECT PLATFORM ====================
def detect_platform(url):
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "tiktok.com" in url:
        return "tiktok"
    elif "facebook.com" in url or "fb.watch" in url:
        return "facebook"
    elif "instagram.com" in url:
        return "instagram"
    return "youtube"  # default

# ==================== SEARCH (using yt-dlp) ====================
async def search_videos(query, max_results=10):
    import yt_dlp
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "default_search": "ytsearch10"}
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, f"ytsearch10:{query}")
            if info and "entries" in info:
                return [{"title": e.get("title", "Unknown"), "channel": e.get("uploader", "Unknown"), "video_id": e.get("id", ""), "url": e.get("webpage_url", "")} for e in info["entries"][:max_results]]
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []

# ==================== DOWNLOAD ====================
async def download_media(url, quality="720p", convert_mp3=False):
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
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
            }
        else:
            h = int(quality[:-1]) if quality[:-1].isdigit() else 720
            ydl_opts = {
                "format": f"bestvideo[height<={h}]+bestaudio/best[height<={h}]",
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
            if convert_mp3 and filename:
                filename = filename.rsplit(".", 1)[0] + ".mp3"
            return filename
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
        await update.message.reply_text(MESSAGES[state.language]["main_menu"], reply_markup=kb_quality(state.language))

async def help_command(update, context):
    lang = get_user_state(update.effective_user.id).language or "en"
    await update.message.reply_text(MESSAGES[lang]["help_text"])

async def language_command(update, context):
    current = get_user_state(update.effective_user.id).language
    text = "اختر اللغة:" if current == "ar" else "Select language:"
    await update.message.reply_text(text, reply_markup=kb_lang())

async def lang_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang_code = query.data.split("_")[1]
    state.language = lang_code
    await query.edit_message_text(MESSAGES[lang_code]["language_selected"])
    await query.message.reply_text(MESSAGES[lang_code]["main_menu"], reply_markup=kb_quality(lang_code))

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
        await query.edit_message_text(msg["main_menu"], reply_markup=kb_quality(lang))
        return
    
    is_mp3 = query.data == "convert_mp3"
    quality = query.data.replace("q_", "") + "p" if not is_mp3 else "720p"
    
    await query.edit_message_text(msg["converting"] if is_mp3 else msg["downloading"])
    
    url = state.current_link or (f"https://www.youtube.com/watch?v={state.current_video_id}" if state.current_video_id else None)
    
    if url:
        filename = await download_media(url, quality, is_mp3)
        if filename and os.path.exists(filename):
            try:
                ext = filename.rsplit(".", 1)[-1].lower()
                if ext in ["mp3", "m4a"]:
                    await query.message.reply_audio(open(filename, "rb"))
                else:
                    await query.message.reply_video(open(filename, "rb"))
                os.remove(filename)
                await query.message.reply_text(msg["success"])
            except Exception as e:
                logger.error(f"Send error: {e}")
                await query.message.reply_text(msg["error"])
        else:
            await query.message.reply_text(msg["error"])
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
        # Auto-detect platform
        state.current_link = text
        state.platform = detect_platform(text)
        state.current_video_id = None
        await update.message.reply_text(msg["select_quality"], reply_markup=kb_quality(lang))
    
    else:
        # Search (YouTube only)
        await update.message.reply_text("⏳ " + msg["search"] + "...")
        results = await search_videos(text)
        state.search_results = results
        
        if not results:
            await update.message.reply_text(msg["no_results"])
            return
        
        response = f'📋┃{msg["search"]} results for "{text}"\n\n'
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
    state.current_link = None
    
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
    app.add_handler(CallbackQueryHandler(quality_callback, pattern="^(q_|convert_|back$)"))
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^video_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
