from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}
search_cache = {}

os.makedirs("downloads", exist_ok=True)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text("Choose language 🌍", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= LANGUAGE =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Facebook 📘", callback_data="fb")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")]
    ]

    await q.edit_message_text("Choose platform 📱", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= PLATFORM =================
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_data[q.from_user.id] = {"platform": q.data}

    txt = "Send link or search 🔎" if q.data == "yt" else "Send link 🔗"
    await q.edit_message_text(txt)


# ================= YOUTUBE SEARCH =================
async def yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            data = ydl.extract_info(f"ytsearch5:{text}", download=False)

        search_cache[update.message.from_user.id] = data["entries"]

        keyboard = [
            [InlineKeyboardButton(v["title"][:45], callback_data=f"vid_{i}")]
            for i, v in enumerate(data["entries"])
        ]

        await update.message.reply_text(
            "Results 🔎",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await update.message.reply_text("Search failed ❌")


# ================= MESSAGE ROUTER =================
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_data:
        return

    platform = user_data[user_id]["platform"]

    # YouTube search
    if platform == "yt" and not text.startswith("http"):
        await yt_search(update, context, text)
        return

    user_data[user_id]["url"] = text

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text("Choose quality 🎯", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= SELECT SEARCH RESULT =================
async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    idx = int(q.data.split("_")[1])

    video = search_cache[uid][idx]
    user_data[uid]["url"] = video["webpage_url"]

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await q.edit_message_text("Choose quality 🎯", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= DOWNLOAD =================
def get_opts(q, mp3=False):
    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
    }

    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"

    if mp3:
        opts["format"] = "bestaudio/best"
    else:
        opts["format"] = f"bestvideo[height<={q}]+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    return opts


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    url = user_data[uid]["url"]
    choice = q.data

    await q.edit_message_text("Downloading... ⏳")

    mp3 = choice == "mp3"
    quality = None if mp3 else choice.split("_")[1]

    try:
        with yt_dlp.YoutubeDL(get_opts(quality, mp3)) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
    except:
        with yt_dlp.YoutubeDL({"format": "best", "outtmpl": "downloads/%(title)s.%(ext)s"}) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

    if not os.path.exists(path):
        path = path.rsplit(".", 1)[0] + ".mp4"

    with open(path, "rb") as f:
        await q.message.reply_document(f)

    os.remove(path)


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang_"))
app.add_handler(CallbackQueryHandler(platform, pattern="yt|tt|fb|ig"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
app.add_handler(CallbackQueryHandler(select_video, pattern="vid_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
