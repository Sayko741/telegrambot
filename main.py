#!/usr/bin/env python3
"""Telegram Bot - Working version"""

import os
import sys
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

user_data = {}

def get_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"lang": None, "link": None, "video_id": None, "action": None}
    return user_data[user_id]

MSG = {
    "ar": {"welcome": "اختر اللغة:", "selected": "✅ تم", "want": "📌 أرسل رابط أو ابحث:", "link": "🔗 أرسل رابط", "search": "🔍 ابحث", "enter_link": "أرسل الرابط:", "enter_search": "أدخل اسم الفيديو:", "down": "⏳ جاري...", "done": "✅ تم!", "error": "❌ خطأ", "no_result": "❌ لا توجد نتائج"},
    "en": {"welcome": "Choose language:", "selected": "✅ Selected", "want": "📌 Send link or search:", "link": "🔗 Send link", "search": "🔍 Search", "enter_link": "Send link:", "enter_search": "Enter video name:", "down": "⏳ Downloading...", "done": "✅ Done!", "error": "❌ Error", "no_result": "❌ No results"}
}

def kb_lang():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇸🇦 العربية", callback_data="la"), InlineKeyboardButton("🇬🇧 English", callback_data="le")]])

def kb_want(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(MSG[lang]["link"], callback_data="dl")], [InlineKeyboardButton(MSG[lang]["search"], callback_data="ds")]])

def kb_download():
    return InlineKeyboardMarkup([[InlineKeyboardButton("📥 Video", callback_data="d_video")], [InlineKeyboardButton("🎵 MP3", callback_data="d_mp3")], [InlineKeyboardButton("⬅️ Back", callback_data="db")]])

async def download_media(url, mp3=False):
    import yt_dlp
    folder = "/tmp"
    os.makedirs(folder, exist_ok=True)
    try:
        opts = {"format": "bestaudio" if mp3 else "best", "outtmpl": f"{folder}/%(id)s.%(ext)s", "quiet": True}
        if mp3:
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
        
        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, url)
            if not info:
                return None
            file = ydl.prepare_filename(info)
            if mp3:
                await asyncio.sleep(0.5)
                file = file.rsplit(".", 1)[0] + ".mp3"
            return file if os.path.exists(file) else None
    except Exception as e:
        logger.error(f"DL error: {e}")
        return None

async def search_videos(q):
    import yt_dlp
    try:
        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = await loop.run_in_executor(None, ydl.extract_info, f"ytsearch5:{q}")
            if info and "entries" in info:
                return [{"t": e.get("title", ""), "c": e.get("uploader", ""), "i": e.get("id", "")} for e in info["entries"]]
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []

async def start(update, context):
    uid = update.effective_user.id
    st = get_state(uid)
    if not st["lang"]:
        await update.message.reply_text(MSG["ar"]["welcome"], reply_markup=kb_lang())
    else:
        await update.message.reply_text(MSG[st["lang"]]["want"], reply_markup=kb_want(st["lang"]))

async def lang_cb(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    st = get_state(uid)
    st["lang"] = q.data[0] + "r"
    await q.edit_message_text(MSG[st["lang"]]["selected"])
    await q.message.reply_text(MSG[st["lang"]]["want"], reply_markup=kb_want(st["lang"]))

async def action_cb(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    st = get_state(uid)
    lang = st["lang"] or "en"
    
    if q.data == "dl":
        st["action"] = "link"
        await q.edit_message_text(MSG[lang]["enter_link"])
    elif q.data == "ds":
        st["action"] = "search"
        await q.edit_message_text(MSG[lang]["enter_search"])

async def msg_h(update, context):
    uid = update.effective_user.id
    st = get_state(uid)
    lang = st["lang"] or "en"
    txt = update.message.text
    
    is_link = "http" in txt.lower() or "www" in txt.lower()
    
    if st["action"] == "link" and is_link:
        st["link"] = txt
        await update.message.reply_text(MSG[lang]["down"])
        f = await download_media(txt)
        if f and os.path.exists(f):
            await update.message.reply_video(open(f, "rb"))
            os.remove(f)
            await update.message.reply_text(MSG[lang]["done"])
        else:
            await update.message.reply_text(MSG[lang]["error"])
    
    elif st["action"] == "search":
        await update.message.reply_text("⏳ Searching...")
        results = await search_videos(txt)
        if not results:
            await update.message.reply_text(MSG[lang]["no_result"])
            return
        
        txt_resp = f'📋┃"{txt}"\n\n'
        for v in results:
            txt_resp += f"🎬 {v['t']}\n👤 {v['c']}\n\n"
        
        btns = [[InlineKeyboardButton(f"▶️ {v['t'][:25]}...", callback_data=f"v_{v['i']}")] for v in results]
        await update.message.reply_text(txt_resp, reply_markup=InlineKeyboardMarkup(btns))
    
    elif st["action"] == "link" and not is_link:
        await update.message.reply_text(MSG[lang]["enter_link"])
    
    else:
        await update.message.reply_text(MSG[lang]["want"], reply_markup=kb_want(lang))

async def video_cb(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    st = get_state(uid)
    lang = st["lang"] or "en"
    
    st["video_id"] = q.data.replace("v_", "")
    await q.edit_message_text(MSG[lang]["down"], reply_markup=kb_download())

async def dl_cb(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    st = get_state(uid)
    lang = st["lang"] or "en"
    
    if q.data == "db":
        st["link"] = None
        st["video_id"] = None
        st["action"] = None
        await q.edit_message_text(MSG[lang]["want"], reply_markup=kb_want(lang))
        return
    
    mp3 = q.data == "d_mp3"
    await q.edit_message_text(MSG[lang]["down"])
    
    url = st["link"] or (f"https://youtube.com/watch?v={st['video_id']}" if st["video_id"] else None)
    
    if not url:
        await q.message.reply_text(MSG[lang]["error"])
        return
    
    f = await download_media(url, mp3)
    if f and os.path.exists(f):
        try:
            if mp3:
                await q.message.reply_audio(open(f, "rb"))
            else:
                await q.message.reply_video(open(f, "rb"))
            os.remove(f)
            await q.message.reply_text(MSG[lang]["done"])
        except Exception as e:
            logger.error(f"Send error: {e}")
            await q.message.reply_text(MSG[lang]["error"])
    else:
        await q.message.reply_text(MSG[lang]["error"])

async def err(update, context):
    logger.error(f"Error: {context.error}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lang_cb, pattern="^l[a,e]$"))
    app.add_handler(CallbackQueryHandler(action_cb, pattern="^d[l,s]$"))
    app.add_handler(CallbackQueryHandler(video_cb, pattern="^v_"))
    app.add_handler(CallbackQueryHandler(dl_cb, pattern="^d_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    app.add_error_handler(err)
    print("🤖 Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
