from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_state = {}

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "اختار اللغة 🌍",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- LANGUAGE ----------------
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = {}

    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")],
        [InlineKeyboardButton("Facebook 📘", callback_data="fb")],
        [InlineKeyboardButton("Twitter/X 🐦", callback_data="tw")]
    ]

    await query.edit_message_text(
        "اختار المنصة 📱",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- PLATFORM ----------------
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id]["platform"] = query.data

    await query.edit_message_text("ابعت اللينك 🔗")


# ---------------- HANDLE MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id not in user_state:
        return

    user_state[user_id]["url"] = text

    keyboard = [
        [InlineKeyboardButton("160p", callback_data="q_160"),
         InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("480p", callback_data="q_480"),
         InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text(
        "اختار الجودة 🎥",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- DOWNLOAD ----------------
async def download_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    choice = query.data
    url = user_state[user_id]["url"]

    await query.edit_message_text("⏳ جاري التحميل...")

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    try:
        if choice == "mp3":
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            }
        else:
            quality = choice.split("_")[1]
            ydl_opts = {
                "format": f"bestvideo[height<={quality}]+bestaudio/best",
                "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, "rb") as f:
            await query.message.reply_document(document=f)

        os.remove(file_path)

    except Exception as e:
        await query.message.reply_text(f"❌ خطأ:\n{e}")


# ---------------- HANDLERS ----------------
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang_"))
app.add_handler(CallbackQueryHandler(platform, pattern="^(yt|tt|ig|fb|tw)$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(download_quality, pattern="^(q_|mp3)$"))

print("Bot Running...")
app.run_polling()
