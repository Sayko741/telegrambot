#!/usr/bin/env python3
"""Telegram Bot - Simple & Working"""

import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== STATE ====================
users = {}

def get_u(id):
    if id not in users:
        users[id] = {"lang": None, "url": None}
    return users[id]

# ==================== MESSAGES ====================
MSG = {
    "ar": {"w": "🎬 اختر:", "s": "✅", "m": "📎 رابط أو ابحث:", "d": "⏳...", "ok": "✅", "e": "❌", "n": "❌ لا", "x": "⏳", "p": "🎬:"},
    "en": {"w": "🎬 Choose:", "s": "✅", "m": "📎 Link or search:", "d": "⏳...", "ok": "✅", "e": "❌", "n": "❌ No", "x": "⏳", "p": "🎬:"}
}

def KB_L():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇸🇦", cb="la"), InlineKeyboardButton("🇬🇧", cb="le")]])

def KB_D():
    return InlineKeyboardMarkup([[InlineKeyboardButton("📥 Video", cb="dv"), InlineKeyboardButton("🎵 MP3", cb="dm")]])

# ==================== DOWNLOAD ====================
async def dl(url, mp3=False):
    import yt_dlp
    folder = "/tmp"
    os.makedirs(folder, exist_ok=True)
    
    try:
        opt = {
            "format": "bestaudio" if mp3 else "best",
            "outtmpl": f"{folder}/%(title)s.%(ext)s",
            "quiet": True,
        }
        if mp3:
            opt["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
        
        with yt_dlp.YoutubeDL(opt) as y:
            info = y.extract_info(url, download=True)
            if not info:
                return None
            return y.prepare_filename(info)
    except Exception as e:
        logger.error(f"DL: {e}")
        return None

# ==================== SEARCH ====================
async def srch(q):
    import yt_dlp
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as y:
            i = y.extract_info(f"ytsearch8:{q}", download=False)
            if i and "entries" in i:
                return [{"t": e.get("title", "?")[:40], "c": e.get("uploader", "?"), "i": e.get("id", "")} for e in i["entries"]]
    except Exception as e:
        logger.error(f"SR: {e}")
    return []

# ==================== HANDLERS ====================
async def start(u, c):
    us = get_u(u.effective_user.id)
    await u.message.reply_text(MSG["ar"]["w"] if not us["lang"] else MSG[us["lang"]]["m"], rep=KB_L() if not us["lang"] else None)

async def lang(u, c):
    q = u.callback_query
    await q.answer()
    us = get_u(q.from_user.id)
    us["lang"] = "ar" if q.data == "la" else "en"
    await q.edit_message_text(MSG[us["lang"]]["s"])
    await q.message.reply_text(MSG[us["lang"]]["m"])

async def msg(u, c):
    us = get_u(u.effective_user.id)
    l = us.get("lang", "en")
    t = u.message.text
    
    link = any(x in t.lower() for x in ["http", "www", ".com", ".be"])
    
    if link:
        await u.message.reply_text(MSG[l]["d"])
        f = await dl(t)
        if f and os.path.exists(f):
            await u.message.reply_video(open(f, "rb"))
            os.remove(f)
            await u.message.reply_text(MSG[l]["ok"])
        else:
            await u.message.reply_text(MSG[l]["e"])
    else:
        await u.message.reply_text(MSG[l]["x"])
        r = await srch(t)
        if not r:
            await u.message.reply_text(MSG[l]["n"])
            return
        txt = f'📋┃"{t}"\n\n'
        bt = []
        for i, v in enumerate(r, 1):
            txt += f"{i}️⃣ {v['t']}\n👤 {v['c']}\n\n"
            bt.append([InlineKeyboardButton(f"▶️ {i}", cb=f"v_{v['i']}")])
        await u.message.reply_text(txt, rep=InlineKeyboardMarkup(bt))

async def vid(u, c):
    q = u.callback_query
    await q.answer()
    us = get_u(q.from_user.id)
    l = us.get("lang", "en")
    us["url"] = f"https://youtube.com/watch?v={q.data.replace('v_', '')}"
    await q.edit_message_text(MSG[l]["p"], rep=KB_D())

async def dwn(u, c):
    q = u.callback_query
    await q.answer()
    us = get_u(q.from_user.id)
    l = us.get("lang", "en")
    
    if q.data == "dm":
        mp = True
    elif q.data == "dv":
        mp = False
    else:
        await q.edit_message_text(MSG[l]["m"])
        return
    
    await q.edit_message_text(MSG[l]["d"])
    f = await dl(us.get("url", ""), mp)
    if f and os.path.exists(f):
        if mp:
            await q.message.reply_audio(open(f, "rb"))
        else:
            await q.message.reply_video(open(f, "rb"))
        os.remove(f)
        await q.message.reply_text(MSG[l]["ok"])
    else:
        await q.message.reply_text(MSG[l]["e"])

async def err(u, c):
    logger.error(f"E: {c.error}")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lang, pattern="^l[ae]$"))
    app.add_handler(CallbackQueryHandler(vid, pattern="^v_"))
    app.add_handler(CallbackQueryHandler(dwn, pattern="^d[vm]$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    app.add_error_handler(err)
    print("🤖 Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
