#!/usr/bin/env python3
"""
Telegram Bot - Download from any platform
Supports: YouTube, TikTok, Facebook, Instagram, Twitter
"""

import os
import sys
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ==================== USER STATE ====================
class UserState:
    def __init__(self):
        self.lang = None          # Language: "ar" or "en"
        self.url = None          # Pending video URL for download
        self.action = None       # "link" or "search"

user_states = {}

def get_user(user_id):
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]

# ==================== MESSAGES ====================
MESSAGES = {
    "ar": {
        "welcome": "🎬 مرحباً! اختر لغتك:",
        "selected": "✅ تم اختيار اللغة",
        "main": "📎 أرسل رابط للتحميل أو اكتب للبحث:",
        "downloading": "⏳ جاري التحميل...",
        "success": "✅ تم التحميل بنجاح!",
        "error": "❌ حدث خطأ. يرجى المحاولة لاحقاً",
        "no_results": "❌ لا توجد نتائج",
        "searching": "⏳ جاري البحث...",
        "select": "🎬 اختر صيغة التحميل:",
        "enter_link": "📎 أرسل الرابط:",
        "enter_search": "📎 أدخل اسم الفيديو:"
    },
    "en": {
        "welcome": "🎬 Hello! Choose your language:",
        "selected": "✅ Language selected",
        "main": "📎 Send link to download or type to search:",
        "downloading": "⏳ Downloading...",
        "success": "✅ Downloaded successfully!",
        "error": "❌ Error. Please try again later",
        "no_results": "❌ No results found",
        "searching": "⏳ Searching...",
        "select": "🎬 Select download format:",
        "enter_link": "📎 Send link:",
        "enter_search": "📎 Enter video name:"
    }
}

# ==================== KEYBOARDS ====================
def language_keyboard():
    """Language selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])

def download_options_keyboard():
    """Video or MP3 selection"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 تحميل Video", callback_data="dl_video")],
        [InlineKeyboardButton("🎵 تحميل MP3", callback_data="dl_mp3")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="dl_back")]
    ])

# ==================== DOWNLOAD FUNCTION ====================
async def download_media(url: str, mp3: bool = False) -> str | None:
    """
    Download video/audio using yt-dlp
    Returns: file path if success, None if failed
    """
    import yt_dlp
    
    download_folder = "/tmp"
    os.makedirs(download_folder, exist_ok=True)
    
    try:
        # Get event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if mp3:
            # MP3 options
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{download_folder}/%(title)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            }
        else:
            # Video options (best quality)
            ydl_opts = {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": f"{download_folder}/%(title)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
            }
        
        logger.info(f"Downloading: {url}, mp3={mp3}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info
            info = await loop.run_in_executor(None, ydl.extract_info, url)
            
            if info is None:
                logger.error("No video info returned")
                return None
            
            # Get filename
            filename = ydl.prepare_filename(info)
            
            # For MP3, wait for conversion
            if mp3:
                await asyncio.sleep(2)
                mp3_filename = filename.rsplit(".", 1)[0] + ".mp3"
                if os.path.exists(mp3_filename):
                    return mp3_filename
                # Check for any MP3 file
                for f in os.listdir(download_folder):
                    if f.endswith(".mp3"):
                        return os.path.join(download_folder, f)
            
            # Return filename if exists
            if os.path.exists(filename):
                return filename
            
            return None
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ==================== SEARCH FUNCTION ====================
async def search_youtube(query: str) -> list[dict]:
    """
    Search YouTube for videos
    Returns: list of video info dicts
    """
    import yt_dlp
    
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        ydl_opts = {"quiet": True, "no_warnings": True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search YouTube
            info = await loop.run_in_executor(None, ydl.extract_info, f"ytsearch10:{query}")
            
            if info and "entries" in info:
                results = []
                for e in info["entries"]:
                    duration = e.get("duration", 0)
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    
                    results.append({
                        "title": e.get("title", "Unknown")[:45],
                        "channel": e.get("uploader", "Unknown"),
                        "duration": f"{minutes}:{seconds:02d}",
                        "video_id": e.get("id", ""),
                        "url": e.get("webpage_url", "")
                    })
                return results
                
    except Exception as e:
        logger.error(f"Search error: {e}")
    
    return []

# ==================== COMMANDS ====================

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    
    if user.lang is None:
        await update.message.reply_text(
            MESSAGES["ar"]["welcome"],
            reply_markup=language_keyboard()
        )
    else:
        await update.message.reply_text(MESSAGES[user.lang]["main"])

# Language callback
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    
    if query.data == "lang_ar":
        user.lang = "ar"
    else:
        user.lang = "en"
    
    await query.edit_message_text(MESSAGES[user.lang]["selected"])
    await query.message.reply_text(MESSAGES[user.lang]["main"])

# Message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lang = user.lang or "en"
    text = update.message.text
    
    # Check if it's a link
    link_patterns = ["http://", "https://", "www.", "youtube.com", "youtu.be", 
                   "tiktok.com", "facebook.com", "fb.watch", "instagram.com", 
                   "twitter.com", "x.com"]
    
    is_link = any(pattern in text.lower() for pattern in link_patterns)
    
    if is_link:
        # It's a link - download immediately
        await update.message.reply_text(MESSAGES[lang]["downloading"])
        
        filename = await download_media(text, mp3=False)
        
        if filename and os.path.exists(filename):
            try:
                await update.message.reply_video(open(filename, "rb"))
                os.remove(filename)
                await update.message.reply_text(MESSAGES[lang]["success"])
            except Exception as e:
                logger.error(f"Send error: {e}")
                await update.message.reply_text(MESSAGES[lang]["error"])
        else:
            await update.message.reply_text(MESSAGES[lang]["error"])
    
    else:
        # It's a search query
        await update.message.reply_text(MESSAGES[lang]["searching"])
        
        results = await search_youtube(text)
        
        if not results:
            await update.message.reply_text(MESSAGES[lang]["no_results"])
            return
        
        # Format results message
        message_text = f'📋┃نتائج البحث عن "{text}"\n' if lang == "ar" else f'📋┃Search results for "{text}"\n'
        message_text += "━" * 25 + "\n\n"
        
        # Create buttons
        buttons = []
        for i, video in enumerate(results, 1):
            message_text += f"{i}️⃣ {video['title']}\n"
            message_text += f"   👤 {video['channel']} • 🕑 {video['duration']}\n\n"
            buttons.append([
                InlineKeyboardButton(
                    f"▶️ {i}",
                    callback_data=f"video_{video['video_id']}"
                )
            ])
        
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# Video selection callback
async def video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    lang = user.lang or "en"
    
    # Get video ID
    video_id = query.data.replace("video_", "")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    user.url = video_url
    
    # Show download options
    await query.edit_message_text(
        MESSAGES[lang]["select"],
        reply_markup=download_options_keyboard()
    )

# Download callback
async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    lang = user.lang or "en"
    
    # Back button
    if query.data == "dl_back":
        user.url = None
        await query.edit_message_text(MESSAGES[lang]["main"])
        return
    
    # MP3 or Video
    mp3 = (query.data == "dl_mp3")
    
    url = user.url
    if not url:
        await query.message.reply_text(MESSAGES[lang]["error"])
        return
    
    # Download
    await query.edit_message_text(MESSAGES[lang]["downloading"])
    
    filename = await download_media(url, mp3=mp3)
    
    if filename and os.path.exists(filename):
        try:
            if mp3:
                await query.message.reply_audio(open(filename, "rb"))
            else:
                await query.message.reply_video(open(filename, "rb"))
            os.remove(filename)
            await query.message.reply_text(MESSAGES[lang]["success"])
        except Exception as e:
            logger.error(f"Send error: {e}")
            await query.message.reply_text(MESSAGES[lang]["error"])
    else:
        await query.message.reply_text(MESSAGES[lang]["error"])

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^video_"))
    app.add_handler(CallbackQueryHandler(download_callback, pattern="^dl_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)
    
    # Start bot
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
