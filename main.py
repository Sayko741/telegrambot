#!/usr/bin/env python3
"""Telegram Bot - Clean & Working"""

import os
import sys
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ==================== STATE ====================
class UserState:
    def __init__(self):
        self.lang = None
        self.action = None
        self.link = None
        self.video_id = None
        self.search_results = []

user_states = {}

def get_user(user_id):
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]

# ==================== MESSAGES ====================
MSG = {
    "ar": {
        "welcome": "🎬 أهلاً! اختر لغتك:",
        "selected": "✅ تم اختيار اللغة",
        "main": "📎 أرسل رابط للتحميل أو اكتب اسم للبحث:",
        "download": "⏳ جاري التحميل...",
        "done": "✅ تم التحميل بنجاح!",
        "error": "❌ حدث خطأ. تحقق من الرابط وحاول снова",
        "no_result": "❌ لم يتم العثور على نتائج",
        "search": "⏳ جاري البحث...",
        "select": "🎬 اختر فيديو للتحميل:"
    },
    "en": {
        "welcome": "🎬 Hello! Choose language:",
        "selected": "✅ Language selected",
        "main": "📎 Send link to download or type to search:",
        "download": "⏳ Downloading...",
        "done": "✅ Downloaded successfully!",
        "error": "❌ Error. Check link and try again",
        "no_result": "❌ No results found",
        "search": "⏳ Searching...",
        "select": "🎬 Select video to download:"
    }
}

# ==================== KEYBOARDS ====================
def kb_lang():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])

def kb_mp3():
    """MP3 or Video download option"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 تحميل Video", callback_data="dl_video")],
        [InlineKeyboardButton("🎵 تحميل MP3", callback_data="dl_mp3")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="dl_back")]
    ])

# ==================== DOWNLOAD ====================
async def download_media(url, mp3=False):
    import yt_dlp
    
    folder = "/tmp"
    os.makedirs(folder, exist_ok=True)
    
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if mp3:
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": f"{folder}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            }
        else:
            ydl_opts = {
                "format": "best",
                "outtmpl": f"{folder}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
            }
        
        logger.info(f"Downloading: {url}, mp3={mp3}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, url)
            if info is None:
                return None
            
            filename = ydl.prepare_filename(info)
            
            if mp3:
                await asyncio.sleep(1.5)
                base = filename.rsplit(".", 1)[0]
                mp3_file = base + ".mp3"
                if os.path.exists(mp3_file):
                    return mp3_file
                # Find any mp3 in folder
                for f in os.listdir(folder):
                    if f.endswith(".mp3"):
                        return os.path.join(folder, f)
                return filename if os.path.exists(filename) else None
            
            return filename if os.path.exists(filename) else None
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ==================== SEARCH ====================
async def search_media(query):
    import yt_dlp
    
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        ydl_opts = {"quiet": True, "no_warnings": True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, f"ytsearch10:{query}")
            
            if info and "entries" in info:
                return [
                    {
                        "title": e.get("title", "Unknown"),
                        "channel": e.get("uploader", "Unknown"),
                        "duration": e.get("duration", 0),
                        "views": e.get("view_count", 0),
                        "video_id": e.get("id", ""),
                        "thumbnail": e.get("thumbnail", "")
                    }
                    for e in info["entries"]
                ]
    except Exception as e:
        logger.error(f"Search error: {e}")
    
    return []

def format_duration(seconds):
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def format_views(views):
    if not views:
        return "0"
    if views >= 1_000_000:
        return f"{views/1_000_000:.1f}M"
    if views >= 1_000:
        return f"{views/1_000:.1f}K"
    return str(views)

# ==================== HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    
    if user.lang is None:
        await update.message.reply_text(MSG["ar"]["welcome"], reply_markup=kb_lang())
    else:
        await update.message.reply_text(MSG[user.lang]["main"])

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    
    # Set language
    user.lang = "ar" if query.data == "lang_ar" else "en"
    
    await query.edit_message_text(MSG[user.lang]["selected"])
    await query.message.reply_text(MSG[user.lang]["main"])

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lang = user.lang or "en"
    text = update.message.text
    
    # Check if it's a link
    is_link = any(p in text.lower() for p in ["http", "www.", ".com", ".be", ".to/", "fb.watch", "youtu.be", "tiktok", "instagram"])
    
    if is_link:
        # It's a link - download immediately
        await update.message.reply_text(MSG[lang]["download"])
        
        filename = await download_media(text, mp3=False)
        
        if filename and os.path.exists(filename):
            try:
                await update.message.reply_video(open(filename, "rb"))
                os.remove(filename)
                await update.message.reply_text(MSG[lang]["done"])
            except Exception as e:
                logger.error(f"Send error: {e}")
                await update.message.reply_text(MSG[lang]["error"])
        else:
            await update.message.reply_text(MSG[lang]["error"])
    
    else:
        # Not a link - search YouTube
        await update.message.reply_text(MSG[lang]["search"])
        
        results = await search_media(text)
        
        if not results:
            await update.message.reply_text(MSG[lang]["no_result"])
            return
        
        user.search_results = results
        
        # Nice formatted results
        msg_text = f"📋 ┃ Results for \"{text}\"\n"
        msg_text += "━" * 25 + "\n\n"
        
        # Create buttons with nice format
        buttons = []
        for i, v in enumerate(results[:7], 1):
            title = v['title'][:40] if len(v['title']) > 40 else v['title']
            duration = format_duration(v.get('duration', 0))
            views = format_views(v.get('views', 0))
            
            # Format message for each result
            msg_text += f"{i}️⃣ {v['title']}\n"
            msg_text += f"   👤 {v['channel']} • 🕑 {duration} • 👁 {views}\n"
            msg_text += f"   🎬 /watch?v={v['video_id']}\n\n"
            
            # Button with index
            buttons.append([
                InlineKeyboardButton(
                    f"▶️ {i} - {title[:25]}...",
                    callback_data=f"vid_{v['video_id']}"
                )
            ])
        
        await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(buttons))

async def video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    lang = user.lang or "en"
    
    # Get video ID
    video_id = query.data.replace("vid_", "")
    user.video_id = video_id
    
    # Show download options
    await query.edit_message_text(
        MSG[lang]["select"],
        reply_markup=kb_mp3()
    )

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    lang = user.lang or "en"
    
    # Back button
    if query.data == "dl_back":
        user.video_id = None
        await query.edit_message_text(MSG[lang]["main"])
        return
    
    # Determine MP3 or Video
    mp3 = (query.data == "dl_mp3")
    
    # Build URL
    url = user.video_id
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={user.video_id}"
    
    await query.edit_message_text(MSG[lang]["download"])
    
    # Download
    filename = await download_media(url, mp3=mp3)
    
    if filename and os.path.exists(filename):
        try:
            if mp3:
                await query.message.reply_audio(open(filename, "rb"))
            else:
                await query.message.reply_video(open(filename, "rb"))
            os.remove(filename)
            await query.message.reply_text(MSG[lang]["done"])
        except Exception as e:
            logger.error(f"Send error: {e}")
            await query.message.reply_text(MSG[lang]["error"])
    else:
        await query.message.reply_text(MSG[lang]["error"])

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^vid_"))
    app.add_handler(CallbackQueryHandler(download_callback, pattern="^dl_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)
    
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
