import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from youtubesearchpython import VideosSearch
import yt_dlp

TOKEN = "PUT_YOUR_BOT_TOKEN"

logging.basicConfig(level=logging.INFO)

# ---------------- KEYBOARDS ---------------- #

main_keyboard = ReplyKeyboardMarkup(
    [["Restart", "Language"], ["Help"]],
    resize_keyboard=True
)

language_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
    [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
])

quality_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("160p", callback_data="q_160"),
     InlineKeyboardButton("360p", callback_data="q_360")],
    [InlineKeyboardButton("720p", callback_data="q_720"),
     InlineKeyboardButton("1080p", callback_data="q_1080")],
    [InlineKeyboardButton("🎵 MP3", callback_data="q_mp3")]
])

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "اختار اللغة 🌍",
        reply_markup=language_keyboard
    )

# ---------------- LANGUAGE ---------------- #

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["lang"] = query.data

    await query.message.reply_text(
        "📩 ابعت الرابط أو اكتب كلمة بحث",
        reply_markup=main_keyboard
    )

# ---------------- MESSAGE HANDLER ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Restart
    if text == "Restart":
        await start(update, context)
        return

    # Help
    if text == "Help":
        await update.message.reply_text(
            "📌 طريقة الاستخدام:\n\n"
            "1- ابعت رابط فيديو\n"
            "2- أو اكتب كلمة بحث\n"
            "3- اختار الجودة\n\n"
            "📩 الدعم: mohamedeslammaklad700@gmail.com"
        )
        return

    # Search (no link)
    if "http" not in text:
        results = VideosSearch(text, limit=4).result()["result"]

        msg = f'📋┃نتائج البحث عن "{text}"\n\n'

        for i, r in enumerate(results):
            msg += (
                f"🎬 {r['title']}\n"
                f"👤 {r['channel']['name']}\n"
                f"🕑 {r['duration']} - 👁 {r['viewCount']['short']}\n"
                f"🔗 /dl_{r['id']}\n\n"
            )

        await update.message.reply_text(msg)
        return

    # If link
    context.user_data["url"] = text

    await update.message.reply_text(
        "اختار الجودة 🎥",
        reply_markup=quality_keyboard
    )

# ---------------- DOWNLOAD ---------------- #

def download_video(url, quality):
    ydl_opts = {
        "format": "best",
        "outtmpl": "video.mp4"
    }

    if quality == "mp3":
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": "audio.mp3",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }]
        }

    elif quality == "160":
        ydl_opts["format"] = "worst[height<=160]"
    elif quality == "360":
        ydl_opts["format"] = "best[height<=360]"
    elif quality == "720":
        ydl_opts["format"] = "best[height<=720]"
    elif quality == "1080":
        ydl_opts["format"] = "best[height<=1080]"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ---------------- CALLBACK ---------------- #

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # language handled above
    if data.startswith("lang"):
        return

    url = context.user_data.get("url")

    if not url:
        await query.message.reply_text("ابعت لينك الأول")
        return

    quality = data.split("_")[1]

    await query.message.reply_text("⏳ جاري التحميل...")

    download_video(url, quality)

    await query.message.reply_document(document=open("video.mp4", "rb"))

# ---------------- MAIN ---------------- #

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(callback_handler))

app.run_polling()
