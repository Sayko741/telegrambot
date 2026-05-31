#!/usr/bin/env python3
"""Telegram Bot - Fixed search flow"""

import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        self.action = None  # "send_link" or "search"

user_states = {}

def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]

# ==================== MESSAGES ====================
MESSAGES = {
    "ar": {
        "welcome": "مرحباً! اختر لغتك:", 
        "language_selected": "✅ تم اختيار العربية",
        "send_or_search": "📎 ماذا تريد؟",
        "send_link_btn": "🔗 أرسل رابط",
        "search_btn": "🔍 بحث",
        "enter_link": "📎 أرسل الرابط للتحميل:",
        "enter_search": "📝 أدخل اسم الفيديو للبحث:",
        "downloading": "⏳ جاري التحميل...",
        "converting": "⏳ جاري التحويل...", 
        "no_results": "❌ لا توجد نتائج", 
        "error": "❌ خطأ. تحقق من الرابط",
        "success": "✅ تم الإرسال بنجاح!",
        "select_quality": "🎬 اختر الجودة أو حمل MP3:",
    },
    "en": {
        "welcome": "Hello! Choose language:", 
        "language_selected": "✅ English selected",
        "send_or_search": "📎 What do you want?",
        "send_link_btn": "🔗 Send link",
        "search_btn": "🔍 Search",
        "enter_link": "📎 Send link to download:",
        "enter_search": "📝 Enter video name to search:",
        "downloading": "⏳ Downloading...",
        "converting": "⏳ Converting...", 
        "no_results": "❌ No results found", 
        "error": "❌ Error. Check the link",
        "success": "✅ Sent successfully!",
        "select_quality": "🎬 Select quality or download MP3:",
    }
}

# ==================== KEYBOARDS ====================
def kb_lang():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    ]])

def kb_send_or_search(lang):
    msg = MESSAGES[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(msg["send_link_btn"], callback_data="action_link")],
        [InlineKeyboardButton(msg["search_btn"], callback_data="action_search")]
    ])

def kb_quality(lang):
    back = "⬅️ رجوع" if lang == "ar" else "⬅️ Back"
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📺 144p", callback_data="q_144"), InlineKeyboardButton("📺 240p", callback_data="q_240"), InlineKeyboardButton("📺 360p", callback_data="q_360")],
            [InlineKeyboardButton("📺 480p", callback_data="q_480"), InlineKeyboardButton("📺 720p", callback_data="q_720"), InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
            [InlineKeyboardButton("🎵 تحميل MP3", callback_data="convert_mp3")],
            [InlineKeyboardButton(back, callback_data="back")]
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 144p", callback_data="q_144"), InlineKeyboardButton("📺 240p", callback_data="q_240"), InlineKeyboardButton("📺 360p", callback_data="q_360")],
        [InlineKeyboardButton("📺 480p", callback_data="q_480"), InlineKeyboardButton("📺 720p", callback_data="q_720"), InlineKeyboardButton("📺 1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 Download MP3", callback_data="convert_mp3")],
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
    elif "twitter.com" in url or "x.com" in url:
        return "twitter"
    return "other"

# ==================== YOUTUBE SEARCH ====================
async def search_videos(query, max_results=10):
    import yt_dlp
    try:
        ydl_opts = {"quiet": True, "no_warnings": True}
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, f"ytsearch10:{query}")
            if info and "entries" in info:
                results = []
                for e in info["entries"][:max_results]:
                    results.append({
                        "title": e.get("title", "Unknown"),
                        "channel": e.get("uploader", "Unknown"),
                        "video_id": e.get("id", ""),
                        "url": e.get("webpage_url", "")
                    })
                return results
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []

# ==================== DOWNLOAD ====================
async def download_media(url, quality="best", convert_mp3=False):
    import yt_dlp
    download_dir = "/tmp"
    os.makedirs(download_dir, exist_ok=True)
    filename = None
    try:
        if convert_mp3:
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
            }
        elif quality == "best":
            ydl_opts = {
                "format": "best",
                "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
            }
        else:
            h = quality[:-1] if quality and quality[:-1].isdigit() else "720"
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

        logger.info(f"Downloading: {url}, quality={quality}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, url)
            if info is None:
                return None
            filename = ydl.prepare_filename(info)
            if convert_mp3 and filename:
                await asyncio.sleep(1)
                base = filename.rsplit(".", 1)[0]
                if os.path.exists(base + ".mp3"):
                    filename = base + ".mp3"
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
        await update.message.reply_text(MESSAGES[state.language]["send_or_search"], reply_markup=kb_send_or_search(state.language))

async def lang_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang_code = query.data.split("_")[1]
    state.language = lang_code
    await query.edit_message_text(MESSAGES[lang_code]["language_selected"])
    await query.message.reply_text(MESSAGES[lang_code]["send_or_search"], reply_markup=kb_send_or_search(lang_code))

async def action_callback(update, context):
    """Handle Send link / Search buttons"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    
    if query.data == "action_link":
        state.action = "send_link"
        await query.edit_message_text(msg["enter_link"])
    elif query.data == "action_search":
        state.action = "search"
        await query.edit_message_text(msg["enter_search"])

async def handle_message(update, context):
    """Handle link or search input"""
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    text = update.message.text
    
    # Check if link
    is_link = any(x in text.lower() for x in ["http", "www.", ".com", ".be", ".to/", "fb.watch", "youtu.be", "vm.tiktok", "x.com", "twitter.com"])
    
    if is_link:
        # User sent a link
        state.current_link = text
        state.platform = detect_platform(text)
        state.current_video_id = None
        await update.message.reply_text(msg["select_quality"], reply_markup=kb_quality(lang))
    
    elif state.action == "search":
        # User searching - YouTube search
        await update.message.reply_text("⏳ " + msg.get("search", "Searching") + "...")
        results = await search_videos(text)
        
        if not results:
            await update.message.reply_text(msg["no_results"])
            return
        
        state.search_results = results
        response = f'📋┃نتائج البحث لـ "{text}"\n\n' if lang == "ar" else f'📋┃Search results for "{text}"\n\n'
        
        for v in results[:5]:
            response += f"🎬 {v['title']}\n"
            response += f"👤 {v['channel']}\n\n"
        
        # Create buttons for each result
        buttons = []
        for v in results[:5]:
            title = v['title'][:35] + "..." if len(v['title']) > 35 else v['title']
            buttons.append([InlineKeyboardButton(f"▶️ {title}", callback_data=f"video_{v['video_id']}")])
        
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif state.action == "send_link":
        # User typed something but not a link - ask for link
        await update.message.reply_text(msg["enter_link"])
    
    else:
        # Show main menu
        await update.message.reply_text(msg["send_or_search"], reply_markup=kb_send_or_search(lang))

async def video_callback(update, context):
    """Handle video selection from search results"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    
    video_id = query.data.replace("video_", "")
    state.current_video_id = video_id
    state.current_link = None
    state.platform = "youtube"
    
    await query.edit_message_text(MESSAGES[lang]["select_quality"], reply_markup=kb_quality(lang))

async def quality_callback(update, context):
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    
    if query.data == "back":
        state.current_link = None
        state.current_video_id = None
        state.action = None
        state.search_results = []
        await query.edit_message_text(msg["send_or_search"], reply_markup=kb_send_or_search(lang))
        return
    
    is_mp3 = query.data == "convert_mp3"
    quality = "best"
    if not is_mp3:
        quality = query.data.replace("q_", "") + "p"
    
    await query.edit_message_text(msg["converting"] if is_mp3 else msg["downloading"])
    
    url = state.current_link
    if not url and state.current_video_id:
        url = f"https://www.youtube.com/watch?v={state.current_video_id}"
    
    if not url:
        await query.message.reply_text(msg["error"])
        return
    
    try:
        filename = await download_media(url, quality, is_mp3)
        
        if filename and os.path.exists(filename):
            try:
                ext = filename.rsplit(".", 1)[-1].lower()
                if ext == "mp3":
                    await query.message.reply_audio(open(filename, "rb"))
                else:
                    await query.message.reply_video(open(filename, "rb"))
                os.remove(filename)
                await query.message.reply_text(msg["success"])
            except Exception as e:
                logger.error(f"Send error: {e}")
                await query.message.reply_text(f"{msg['error']}: {str(e)}")
        else:
            await query.message.reply_text(msg["error"])
    except Exception as e:
        logger.error(f"Download exception: {e}")
        await query.message.reply_text(f"{msg['error']}: {str(e)}")

async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(action_callback, pattern="^action_"))
    app.add_handler(CallbackQueryHandler(quality_callback, pattern="^(q_|convert_|back$)"))
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^video_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
