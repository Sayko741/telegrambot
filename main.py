from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_lang = {}
search_cache = {}

os.makedirs("downloads", exist_ok=True)


TEXT = {
    "ar": {
        "choose_lang": "اختار اللغة 🌍",
        "send": "ارسل الرابط أو اكتب كلمة للبحث 🔎",
        "quality": "اختار الجودة 🎯",
        "downloading": "⏳ جاري التحميل...",
        "search_fail": "فشل البحث ❌"
    },
    "en": {
        "choose_lang": "Choose language 🌍",
        "send": "Send link or type a search 🔎",
        "quality": "Choose quality 🎯",
        "downloading": "⏳ Downloading...",
        "search_fail": "Search failed ❌"
    }
}


def t(uid, key):
    lang = user_lang.get(uid, "en")
    return TEXT[lang][key]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text("🌍", reply_markup=InlineKeyboardMarkup(keyboard))


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    lang = q.data.split("_")[1]
    user_lang[q.from_user.id] = lang

    await q.edit_message_text(t(q.from_user.id, "send"))


async def yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.message.from_user.id

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            data = ydl.extract_info(f"ytsearch5:{text}", download=False)

        search_cache[uid] = data["entries"]

        keyboard = [
            [InlineKeyboardButton(v["title"][:45], callback_data=f"vid_{i}")]
            for i, v in enumerate(data["entries"])
        ]

        await update.message.reply_text(
            "🔎",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except:
        await update.message.reply_text(t(uid, "search_fail"))


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    if uid not in user_lang:
        return

    if text.startswith("http"):
        user_lang[uid + 1000] = text

        keyboard = [
            [InlineKeyboardButton("1080p", callback_data="q_1080")],
            [InlineKeyboardButton("720p", callback_data="q_720")],
            [InlineKeyboardButton("480p", callback_data="q_480")],
            [InlineKeyboardButton("360p", callback_data="q_360")],
            [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
        ]

        await update.message.reply_text(
            t(uid, "quality"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await yt_search(update, context, text)


async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    idx = int(q.data.split("_")[1])

    video = search_cache[uid][idx]
    user_lang[uid + 1000] = video["webpage_url"]

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await q.edit_message_text(t(uid, "quality"), reply_markup=InlineKeyboardMarkup(keyboard))


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
    url = user_lang.get(uid + 1000)
    choice = q.data

    await q.edit_message_text(t(uid, "downloading"))

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


app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
app.add_handler(CallbackQueryHandler(select_video, pattern="vid_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
