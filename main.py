import os
import yt_dlp
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# ---------------- UI ---------------- #

main_kb = ReplyKeyboardMarkup(
    [["Restart", "Language"], ["Help"]],
    resize_keyboard=True
)

lang_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🇪🇬 عربي", callback_data="ar")],
    [InlineKeyboardButton("🇬🇧 English", callback_data="en")]
])

quality_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("160p", callback_data="160"),
     InlineKeyboardButton("360p", callback_data="360")],
    [InlineKeyboardButton("720p", callback_data="720"),
     InlineKeyboardButton("1080p", callback_data="1080")],
    [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌍 اختار اللغة", reply_markup=lang_kb)

# ---------------- LANGUAGE ---------------- #

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    context.user_data["lang"] = q.data

    await q.message.reply_text(
        "📩 ابعت رابط فيديو أو اكتب بحث",
        reply_markup=main_kb
    )

# ---------------- SEARCH YOUTUBE ---------------- #

def yt_search(query):
    import requests

    search_url = f"https://www.youtube.com/results?search_query={query}"
    return search_url

# ---------------- DOWNLOAD ---------------- #

def download(url, quality):
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "quiet": True
    }

    if quality == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }]
        })
    else:
        ydl_opts["format"] = f"best[height<={quality}]"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ---------------- MESSAGE ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Restart":
        return await start(update, context)

    if text == "Help":
        return await update.message.reply_text(
            "📌 ابعت رابط أو كلمة بحث\n📩 support: mohamedeslammaklad700@gmail.com"
        )

    # SEARCH MODE
    if "http" not in text:
        await update.message.reply_text(
            f"📋┃نتائج البحث عن \"{text}\"\n\n"
            f"🔎 https://www.youtube.com/results?search_query={text}"
        )
        return

    # LINK MODE
    context.user_data["url"] = text
    await update.message.reply_text("🎥 اختار الجودة:", reply_markup=quality_kb)

# ---------------- CALLBACK ---------------- #

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    # language
    if data in ["ar", "en"]:
        return await language(update, context)

    url = context.user_data.get("url")

    if not url:
        return await q.message.reply_text("ابعت لينك الأول")

    await q.message.reply_text("⏳ جاري التحميل...")

    try:
        download(url, data)

        file = "video.mp4" if data != "mp3" else "video.mp3"

        with open(file, "rb") as f:
            await q.message.reply_document(f)

    except Exception as e:
        await q.message.reply_text(f"❌ Error: {str(e)}")

# ---------------- MAIN ---------------- #

def main():
    if not TOKEN:
        raise Exception("BOT_TOKEN missing in Railway")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback))

    app.run_polling()

if __name__ == "__main__":
    main()
