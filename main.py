import os
import yt_dlp
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# ---------------- KEYBOARDS ---------------- #

lang_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
    [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
])

type_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎬 Video", callback_data="video")],
    [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
])

quality_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("160p", callback_data="q_160"),
        InlineKeyboardButton("360p", callback_data="q_360")
    ],
    [
        InlineKeyboardButton("480p", callback_data="q_480"),
        InlineKeyboardButton("720p", callback_data="q_720")
    ],
    [
        InlineKeyboardButton("1080p", callback_data="q_1080")
    ]
])

# ---------------- SEARCH (STABLE) ---------------- #

def search_youtube(query):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch5:{query}", download=False)

    return info.get("entries", [])

# ---------------- DOWNLOAD ---------------- #

def download(url, mode, quality=None):
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "quiet": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "format": "bestvideo+bestaudio/best",
    }

    if mode == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }]
        })
    else:
        ydl_opts["format"] = f"best[height<={quality}]/best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 اختار اللغة",
        reply_markup=lang_kb
    )

# ---------------- MESSAGE ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # 🔎 SEARCH MODE
    if "http" not in text:
        try:
            results = search_youtube(text)
            context.user_data["results"] = results

            msg = f'📋┃نتائج البحث عن "{text}"\n\n'

            for i, r in enumerate(results):
                msg += (
                    f"🎬 {r.get('title')}\n"
                    f"🔗 /v{i}\n\n"
                )

            await update.message.reply_text(msg)

        except Exception as e:
            await update.message.reply_text(f"❌ Search error: {e}")

        return

    # 🔗 LINK MODE
    context.user_data["url"] = text
    await update.message.reply_text("🎥 Video ولا MP3؟", reply_markup=type_kb)

# ---------------- SELECT VIDEO ---------------- #

async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.startswith("/v"):
        return

    try:
        index = int(text.replace("/v", ""))
        results = context.user_data.get("results")

        if not results:
            return await update.message.reply_text("❌ اعمل بحث الأول")

        video = results[index]
        context.user_data["url"] = video["url"]

        await update.message.reply_text(
            f"🎬 {video['title']}\n\nاختار الجودة:",
            reply_markup=quality_kb
        )

    except:
        await update.message.reply_text("❌ Error")

# ---------------- CALLBACK ---------------- #

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    url = context.user_data.get("url")

    if data.startswith("lang"):
        return await q.message.edit_text("🔎 ابعت اسم فيديو أو رابط")

    if not url:
        return await q.message.reply_text("ابعت فيديو الأول")

    # 🎵 MP3
    if data == "mp3":
        await q.message.edit_text("⏳ جاري تحميل MP3...")

        download(url, "mp3")

        with open("video.mp3", "rb") as f:
            await q.message.reply_document(f)

        return

    # 🎬 QUALITY
    if data.startswith("q_"):
        quality = data.split("_")[1]

        await q.message.edit_text(f"⏳ جاري التحميل {quality}p...")

        download(url, "video", quality)

        with open("video.mp4", "rb") as f:
            await q.message.reply_document(f)

        return

    # 🎬 TYPE
    if data in ["video", "mp3"]:
        if data == "video":
            await q.message.edit_text("🎥 اختار الجودة:", reply_markup=quality_kb)
        else:
            await q.message.edit_text("⏳ جاري التحميل MP3...")

            download(url, "mp3")

            with open("video.mp3", "rb") as f:
                await q.message.reply_document(f)

# ---------------- MAIN ---------------- #

def main():
    if not TOKEN:
        raise Exception("BOT_TOKEN missing")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_video))
    app.add_handler(CallbackQueryHandler(callback))

    app.run_polling()

if __name__ == "__main__":
    main()
