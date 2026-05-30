from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

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


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text("🌍", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= LANGUAGE =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    lang = q.data.split("_")[1]
    user_lang[q.from_user.id] = lang

    await q.edit_message_text(t(q.from_user.id, "send"))


# ================= YOUTUBE SEARCH (API) =================
async def yt_search(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.message.from_user.id

    try:
        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            "part": "snippet",
            "q": text,
            "type": "video",
            "maxResults": 5,
            "key": YOUTUBE_API_KEY
        }

        r = requests.get(url, params=params)
        data = r.json()

        results = []

        for item in data["items"]:
            results.append({
                "title": item["snippet"]["title"],
                "webpage_url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })

        search_cache[uid] = results

        keyboard = [
            [InlineKeyboardButton(v["title"][:45], callback_data=f"vid_{i}")]
            for i, v in enumerate(results)
        ]

        await update.message.reply_text(
            "🔎",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print("YT SEARCH ERROR:", e)
        await update.message.reply_text(t(uid, "search_fail"))


# ================= MESSAGE ROUTER =================
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


# ================= SELECT VIDEO =================
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


# ================= DOWNLOAD OPTIONS =================
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
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["format"] = f"bestvideo[height<={q}]+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    return opts


# ================= DOWNLOAD =================
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

    except Exception as e:
        print("DOWNLOAD ERROR:", e)
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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
app.add_handler(CallbackQueryHandler(select_video, pattern="vid_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
