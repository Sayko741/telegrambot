from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}

os.makedirs("downloads", exist_ok=True)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="en")]
    ]

    await update.message.reply_text(
        "اختار اللغة 🌍",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= LANGUAGE =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Facebook 📘", callback_data="fb")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")]
    ]

    await query.edit_message_text(
        "اختار المنصة 📱",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= PLATFORM =================
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data[query.from_user.id] = {"platform": query.data}

    await query.edit_message_text("ابعت اللينك 🔗")


# ================= MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        return

    user_data[user_id]["url"] = text

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text(
        "اختار الجودة 🎯",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= DOWNLOAD =================
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_data[user_id]["url"]
    choice = query.data

    await query.edit_message_text("⏳ جاري التحميل...")

    try:
        if choice == "mp3":
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": "downloads/%(title)s.%(ext)s"
            }
        else:
            quality = choice.split("_")[1]
            ydl_opts = {
                "format": f"bestvideo[height<={quality}]+bestaudio/best",
                "outtmpl": "downloads/%(title)s.%(ext)s",
                "merge_output_format": "mp4"
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        if not os.path.exists(file_path):
            file_path = file_path.rsplit(".", 1)[0] + ".mp4"

        with open(file_path, "rb") as f:
            await query.message.reply_document(f)

        os.remove(file_path)

    except Exception as e:
        await query.message.reply_text(f"❌ خطأ:\n{e}")


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="ar|en"))
app.add_handler(CallbackQueryHandler(platform, pattern="yt|tt|fb|ig"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
