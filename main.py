import os
import logging
import yt_dlp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from youtubesearchpython import VideosSearch

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# ---------------- KEYBOARDS ---------------- #

menu_kb = ReplyKeyboardMarkup(
    [["Restart", "Help"]],
    resize_keyboard=True
)

lang_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
    [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
])

type_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎬 Video", callback_data="video")],
    [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
])

quality_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("160p", callback_data="160"),
     InlineKeyboardButton("360p", callback_data="360")],
    [InlineKeyboardButton("720p", callback_data="720"),
     InlineKeyboardButton("1080p", callback_data="1080")]
])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 اختار اللغة / Choose language",
        reply_markup=lang_kb
    )

# ---------------- LANGUAGE ---------------- #

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    context.user_data["lang"] = q.data

    await q.message.reply_text(
        "🔎 ابعت اسم فيديو أو رابط",
        reply_markup=menu_kb
    )

# ---------------- MESSAGE ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Restart":
        return await start(update, context)

    if text == "Help":
        return await update.message.reply_text(
            "📌 اكتب اسم فيديو أو ابعت رابط\n🎥 اختار جودة أو MP3 بعد كده\n📩 support: mohamedeslammaklad700@gmail.com"
        )

    # 🔎 SEARCH MODE
    if "http" not in text:
        try:
            results = VideosSearch(text, limit=5).result()["result"]
            context.user_data["results"] = results

            msg = f'📋┃نتائج البحث عن "{text}"\n\n'

            for i, r in enumerate(results):
                msg += (
                    f"🎬 {r['title']}\n"
                    f"👤 {r['channel']['name']}\n"
                    f"🕒 {r['duration']} - 👁 {r['viewCount']['short']}\n"
                    f"🎯 /v{i}\n\n"
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
        context.user_data["url"] = video["link"]

        await update.message.reply_text(
            f"🎬 {video['title']}\n\nاختار النوع:",
            reply_markup=type_kb
        )

    except:
        await update.message.reply_text("❌ Error")

# ---------------- CALLBACK ---------------- #

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    url = context.user_data.get("url")

    # 🌍 LANGUAGE
    if data.startswith("lang"):
        return await language_handler(update, context)

    # 🎬 TYPE (video/mp3)
    if data in ["video", "mp3"]:
        if not url:
            return await q.message.reply_text("ابعت لينك الأول")

        context.user_data["mode"] = data

        if data == "video":
            await q.message.reply_text("🎥 اختار الجودة:", reply_markup=quality_kb)
        else:
            await download_and_send(q, url, "mp3")

        return

    # 🎯 QUALITY
    if data in ["160", "360", "720", "1080"]:
        await download_and_send(q, url, "video", data)

# ---------------- DOWNLOAD ---------------- #

def download(url, mode, quality=None):
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "quiet": True
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
        ydl_opts["format"] = f"best[height<={quality}]"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ---------------- SEND ---------------- #

async def download_and_send(query, url, mode, quality=None):
    await query.message.reply_text("⏳ جاري التحميل...")

    try:
        download(url, mode, quality)

        file = "video.mp4" if mode == "video" else "video.mp3"

        with open(file, "rb") as f:
            await query.message.reply_document(f)

    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")

# ---------------- MAIN ---------------- #

def main():
    if not TOKEN:
        raise Exception("BOT_TOKEN missing in Railway")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_video))
    app.add_handler(CallbackQueryHandler(callback))

    app.run_polling()

if __name__ == "__main__":
    main()
