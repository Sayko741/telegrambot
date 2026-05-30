import os
import yt_dlp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

# ---------------- TEXTS ---------------- #

TEXTS = {
    "ar": {
        "choose_lang": "🌍 اختار اللغة",
        "send": "🔎 ابعت اسم فيديو أو رابط",
        "type": "🎥 Video ولا MP3؟",
        "quality": "🎬 اختار الجودة",
        "downloading": "⏳ جاري التحميل...",
        "error": "❌ حصل خطأ"
    },
    "en": {
        "choose_lang": "🌍 Choose language",
        "send": "🔎 Send video name or link",
        "type": "🎥 Video or MP3?",
        "quality": "🎬 Choose quality",
        "downloading": "⏳ Downloading...",
        "error": "❌ Error happened"
    }
}

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

# ---------------- SEARCH ---------------- #

def search_youtube(query):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        return ydl.extract_info(f"ytsearch5:{query}", download=False)["entries"]

# ---------------- DOWNLOAD ---------------- #

def download(url, mode, quality=None):
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "noplaylist": True,
        "quiet": False,
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
        ydl_opts["format"] = f"best[height<={quality}]/best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lang"] = "ar"
    await update.message.reply_text(TEXTS["ar"]["choose_lang"], reply_markup=lang_kb)

# ---------------- MESSAGE ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get("lang", "ar")

    # 🔎 SEARCH
    if "http" not in text:
        try:
            results = search_youtube(text)
            context.user_data["results"] = results

            msg = f'📋 نتائج "{text}"\n\n'
            for i, r in enumerate(results):
                msg += f"🎬 {r['title']}\n🎯 /v{i}\n\n"

            await update.message.reply_text(msg)

        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

        return

    # 🔗 LINK
    context.user_data["url"] = text
    await update.message.reply_text(TEXTS[lang]["type"], reply_markup=type_kb)

# ---------------- SELECT VIDEO ---------------- #

async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.startswith("/v"):
        return

    try:
        i = int(text.replace("/v", ""))
        video = context.user_data["results"][i]

        context.user_data["url"] = video["webpage_url"]

        lang = context.user_data.get("lang", "ar")

        await update.message.reply_text(
            f"🎬 {video['title']}\n\n{TEXTS[lang]['quality']}",
            reply_markup=quality_kb
        )

    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

# ---------------- CALLBACK ---------------- #

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    url = context.user_data.get("url")
    lang = context.user_data.get("lang", "ar")

    # 🌍 LANGUAGE
    if data.startswith("lang"):
        context.user_data["lang"] = data.split("_")[1]
        return await q.message.edit_text(TEXTS[context.user_data["lang"]]["send"])

    if not url:
        return await q.message.reply_text("❌ ابعت فيديو الأول")

    await q.message.edit_text(TEXTS[lang]["downloading"])

    try:
        # 🎵 MP3
        if data == "mp3":
            download(url, "mp3")
            with open("video.mp3", "rb") as f:
                await q.message.reply_document(f)

        # 🎬 VIDEO QUALITY
        elif data.startswith("q_"):
            quality = data.split("_")[1]
            download(url, "video", quality)
            with open("video.mp4", "rb") as f:
                await q.message.reply_document(f)

        # 🎬 DEFAULT VIDEO
        elif data == "video":
            download(url, "video", 720)
            with open("video.mp4", "rb") as f:
                await q.message.reply_document(f)

    except Exception as e:
        await q.message.edit_text(f"❌ Error:\n{e}")

# ---------------- MAIN ---------------- #

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_video))
    app.add_handler(CallbackQueryHandler(callback))

    app.run_polling()

if __name__ == "__main__":
    main()
