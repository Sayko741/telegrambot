import os
import yt_dlp

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
        "choose": "🎥 اختار Video أو MP3",
        "quality": "🎬 اختار الجودة",
        "downloading": "⏳ جاري التحميل...",
        "invalid": "❌ ابعت لينك صحيح"
    },
    "en": {
        "start": "🌍 Choose language",
        "send": "📌 Send video link",
        "choose": "🎥 Choose Video or MP3",
        "quality": "🎬 Choose quality",
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

quality_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("160", callback_data="q_160"),
        InlineKeyboardButton("360", callback_data="q_360")
    ],
    [
        InlineKeyboardButton("480", callback_data="q_480"),
        InlineKeyboardButton("720", callback_data="q_720")
    ],
    [
        InlineKeyboardButton("1080", callback_data="q_1080")
    ]
])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lang"] = "ar"
    await update.message.reply_text(TEXT["ar"]["start"], reply_markup=lang_kb)

# ---------------- MESSAGE ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get("lang", "ar")

    if "http" not in text:
        return await update.message.reply_text(TEXT[lang]["invalid"])

    context.user_data["url"] = text
    await update.message.reply_text(TEXT[lang]["choose"], reply_markup=type_kb)

# ---------------- DOWNLOAD ---------------- #

def download(url, mode, quality=None):
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "ffmpeg_location": "/usr/bin/ffmpeg",
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
        ydl_opts["format"] = f"bestvideo[height={quality}]+bestaudio/best[height={quality}]"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ---------------- CALLBACK ---------------- #

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    url = context.user_data.get("url")
    lang = context.user_data.get("lang", "ar")

    # 🌍 LANGUAGE
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        context.user_data["lang"] = lang
        return await q.message.edit_text(TEXT[lang]["send"])

    if not url:
        return await q.message.reply_text(TEXT[lang]["invalid"])

    await q.message.edit_text(TEXT[lang]["downloading"])

    try:
        # 🎵 MP3
        if data == "mp3":
            download(url, "mp3")
            with open("video.mp3", "rb") as f:
                await q.message.reply_document(f)

        # 🎬 VIDEO → show quality
        elif data == "video":
            await q.message.edit_text(TEXT[lang]["quality"], reply_markup=quality_kb)

        # 🎬 QUALITY DOWNLOAD
        elif data.startswith("q_"):
            quality = data.split("_")[1]
            download(url, "video", quality)

            with open("video.mp4", "rb") as f:
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
