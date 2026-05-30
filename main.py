import os
import yt_dlp
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

# ---------------- TEXT ---------------- #

TEXT = {
    "ar": {
        "start": "🌍 اختار اللغة",
        "send": "📌 ابعت لينك الفيديو",
        "choose": "🎥 Video أو MP3",
        "downloading": "⏳ جاري التحميل...",
        "invalid": "❌ ابعت لينك صحيح"
    },
    "en": {
        "start": "🌍 Choose language",
        "send": "📌 Send video link",
        "choose": "🎥 Video or MP3",
        "downloading": "⏳ Downloading...",
        "invalid": "❌ Send valid link"
    }
}

# ---------------- KEYBOARDS ---------------- #

lang_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    ]
])

type_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎬 Video", callback_data="video")],
    [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌍 Choose language / اختار اللغة", reply_markup=lang_kb)

# ---------------- MESSAGE ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get("lang", "ar")

    if "http" not in text:
        return await update.message.reply_text(TEXT[lang]["invalid"])

    context.user_data["url"] = text
    await update.message.reply_text(TEXT[lang]["choose"], reply_markup=type_kb)

# ---------------- DOWNLOAD ---------------- #

def download(url, mode):
    file_id = str(uuid.uuid4())

    ydl_opts = {
        "outtmpl": f"{file_id}.%(ext)s",
        "noplaylist": True,
        "quiet": True,
    }

    if mode == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        })
    else:
        ydl_opts["format"] = "best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return file_id

# ---------------- CALLBACK ---------------- #

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    url = context.user_data.get("url")

    # 🌍 LANGUAGE
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        context.user_data["lang"] = lang
        return await q.message.edit_text(TEXT[lang]["send"])

    lang = context.user_data.get("lang", "ar")

    if not url:
        return await q.message.reply_text(TEXT[lang]["invalid"])

    await q.message.edit_text(TEXT[lang]["downloading"])

    try:
        file_id = download(url, data)

        # 🎵 MP3
        if data == "mp3":
            path = f"{file_id}.mp3"
            with open(path, "rb") as f:
                await q.message.reply_document(f)

        # 🎬 VIDEO
        else:
            path = f"{file_id}.mp4"
            with open(path, "rb") as f:
                await q.message.reply_document(f)

    except Exception as e:
        await q.message.edit_text(f"❌ Error:\n{e}")

# ---------------- MAIN ---------------- #

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback))

    app.run_polling()

if __name__ == "__main__":
    main()
