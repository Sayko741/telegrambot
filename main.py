from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}
search_cache = {}

os.makedirs("downloads", exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="en")]
    ]
    await update.message.reply_text("اختار اللغة 🌍", reply_markup=InlineKeyboardMarkup(keyboard))


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Facebook 📘", callback_data="fb")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")]
    ]

    await query.edit_message_text("اختار المنصة 📱", reply_markup=InlineKeyboardMarkup(keyboard))


async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data[query.from_user.id] = {"platform": query.data}

    await query.edit_message_text("ابعت لينك أو كلمة بحث 🔎")


async def youtube_search(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        result = ydl.extract_info(f"ytsearch5:{text}", download=False)

    search_cache[update.message.from_user.id] = result["entries"]

    keyboard = [
        [InlineKeyboardButton(v["title"][:50], callback_data=f"vid_{i}")]
        for i, v in enumerate(result["entries"])
    ]

    await update.message.reply_text("🔎 نتائج البحث:", reply_markup=InlineKeyboardMarkup(keyboard))


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        return

    if user_data[user_id]["platform"] == "yt" and not text.startswith("http"):
        await youtube_search(update, context, text)
        return

    user_data[user_id]["url"] = text

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text("اختار الجودة 🎯", reply_markup=InlineKeyboardMarkup(keyboard))


async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    index = int(query.data.split("_")[1])

    video = search_cache[user_id][index]
    user_data[user_id]["url"] = video["webpage_url"]

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await query.edit_message_text("اختار الجودة 🎯", reply_markup=InlineKeyboardMarkup(keyboard))


def get_opts(quality=None, mp3=False):
    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True
    }

    if mp3:
        opts["format"] = "bestaudio/best"
    else:
        opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"

    return opts


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_data[user_id]["url"]
    choice = query.data

    await query.edit_message_text("⏳ جاري التحميل...")

    mp3 = choice == "mp3"
    quality = None if mp3 else choice.split("_")[1]

    try:
        with yt_dlp.YoutubeDL(get_opts(quality, mp3)) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
    except:
        with yt_dlp.YoutubeDL({"outtmpl": "downloads/%(title)s.%(ext)s", "format": "best"}) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

    if not os.path.exists(file_path):
        file_path = file_path.rsplit(".", 1)[0] + ".mp4"

    with open(file_path, "rb") as f:
        await query.message.reply_document(f)

    os.remove(file_path)


app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="ar|en"))
app.add_handler(CallbackQueryHandler(platform, pattern="yt|tt|fb|ig"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
app.add_handler(CallbackQueryHandler(select_video, pattern="^vid_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
