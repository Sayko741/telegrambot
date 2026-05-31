#!/usr/bin/env python3
"""Telegram Bot - Simple & Working"""

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
        self.current_video_id = None
        self.action = None

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
        "no_results": "❌ لا توجد نتائج", 
        "error": "❌ خطأ",
        "success": "✅ تم بنجاح!",
    },
    "en": {
        "welcome": "Hello! Choose language:", 
        "language_selected": "✅ English selected",
        "send_or_search": "📎 What do you want?",
        "send_link_btn": "🔗 Send link",
        "search_btn": "🔍 Search",
        "enter_link": "📎 Send link to download:",
        "enter_search": "📝 Enter video name:",
        "downloading": "⏳ Downloading...",
        "no_results": "❌ No results found", 
        "error": "❌ Error",
        "success": "✅ Done!",
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

# ==================== DOWNLOAD ====================
async def download_media(url):
    import yt_dlp
    download_dir = "/tmp"
    os.makedirs(download_dir, exist_ok=True)
    filename = None
    try:
        ydl_opts = {
            "format": "best",
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
            return filename
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

# ==================== SEARCH ====================
async def search_videos(query):
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
                return [{"title": e.get("title", ""), "channel": e.get("uploader", ""), "video_id": e.get("id", "")} for e in info["entries"][:5]]
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []

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
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    text = update.message.text
    
    # Check if link
    is_link = "http" in text.lower() or "www." in text.lower() or ".com" in text.lower()
    
    if is_link:
        state.current_link = text
        state.current_video_id = None
        await update.message.reply_text(msg["downloading"])
        
        filename = await download_media(text)
        
        if filename and os.path.exists(filename):
            try:
                await update.message.reply_video(open(filename, "rb"))
                os.remove(filename)
                await update.message.reply_text(msg["success"])
            except Exception as e:
                logger.error(f"Send error: {e}")
                await update.message.reply_text(msg["error"])
        else:
            await update.message.reply_text(msg["error"])
    
    elif state.action == "search":
        await update.message.reply_text("⏳ " + msg.get("search", "Searching") + "...")
        results = await search_videos(text)
        
        if not results:
            await update.message.reply_text(msg["no_results"])
            return
        
        response = f'📋┃"{text}"\n\n'
        for v in results:
            response += f"🎬 {v['title']}\n👤 {v['channel']}\n\n"
        
        buttons = [[InlineKeyboardButton(f"▶️ {v['title'][:30]}...", callback_data=f"video_{v['video_id']}")] for v in results]
        
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif state.action == "send_link":
        await update.message.reply_text(msg["enter_link"])
    
    else:
        await update.message.reply_text(msg["send_or_search"], reply_markup=kb_send_or_search(lang))

async def video_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = get_user_state(user_id)
    lang = state.language or "en"
    msg = MESSAGES[lang]
    
    video_id = query.data.replace("video_", "")
    state.current_video_id = video_id
    state.current_link = None
    
    await query.edit_message_text(msg["downloading"])
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    filename = await download_media(url)
    
    if filename and os.path.exists(filename):
        try:
            await query.message.reply_video(open(filename, "rb"))
            os.remove(filename)
            await query.message.reply_text(msg["success"])
        except Exception as e:
            logger.error(f"Send error: {e}")
            await query.message.reply_text(msg["error"])
    else:
        await query.message.reply_text(msg["error"])

async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(action_callback, pattern="^action_"))
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^video_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
