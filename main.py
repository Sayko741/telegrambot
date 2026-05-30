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

# ================= TEXT =================
TEXT = {
    "ar": {
        "choose_lang": "اختار اللغة 🌍",
        "send": "ارسل الرابط أو اكتب كلمة للبحث 🔎",
        "quality": "اختار الجودة 🎯",
        "downloading": "⏳ جاري التحميل...",
        "search_fail": "فشل البحث ❌"
    }
}

def t(uid, key):
    return TEXT.get(user_lang.get(uid, "ar"), TEXT["ar"])[key]


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Start", callback_data="start")],
        [InlineKeyboardButton("🌍 Language", callback_data="lang_menu")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")]
    ]

    await update.message.reply_text(
        "👋 Welcome",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= MENU =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "help":
        await q.edit_message_text(
            "📌 استخدم البوت:\n- اكتب بحث 🔎\n- ابعت لينك 🎬\n- اختار الجودة 🎯",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Back", callback_data="back")]
            ])
        )

    elif q.data in ["back", "restart", "start"]:
        await q.edit_message_text("🔎 ابعت بحث أو رابط")

    elif q.data == "lang_menu":
        await q.edit_message_text(
            "🌍 اختار اللغة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
            ])
        )


# ================= LANGUAGE =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_lang[q.from_user.id] = q.data.split("_")[1]
    await q.edit_message_text("✅ تم اختيار اللغة")


# ================= YOUTUBE SEARCH =================
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
        message = f'📋┃نتائج البحث عن "{text}"\n\n'

        for item in data["items"]:
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]

            # views (optional fallback)
            views = "N/A"

            results.append(vid)

            message += f"""🎬 {title}
👤 {channel}
🕑 -- - 👁 {views}
🔗 /dl_{vid}

"""

        search_cache[uid] = results

        await update.message.reply_text(message)

    except Exception as e:
        print("SEARCH ERROR:", e)
        await update.message.reply_text("Search failed ❌")


# ================= MESSAGE ROUTER =================
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    if text.startswith("http"):
        user_lang[uid + 1000] = text

        await update.message.reply_text(
            "🎯 اختر الجودة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1080p", callback_data="q_1080")],
                [InlineKeyboardButton("720p", callback_data="q_720")],
                [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
            ])
        )
        return

    await yt_search(update, context, text)


# ================= /DL COMMAND =================
async def dl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text.startswith("/dl_"):
        vid = text.replace("/dl_", "")
        url = f"https://www.youtube.com/watch?v={vid}"

        user_lang[update.message.from_user.id + 1000] = url

        await update.message.reply_text(
            "🎯 اختر الجودة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1080p", callback_data="q_1080")],
                [InlineKeyboardButton("720p", callback_data="q_720")],
                [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
            ])
        )


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

    await q.edit_message_text("⏳ جاري التحميل...")

    mp3 = choice == "mp3"
    quality = None if mp3 else choice.split("_")[1]

    try:
        with yt_dlp.YoutubeDL(get_opts(quality, mp3)) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

    except Exception as e:
        print("DOWNLOAD ERROR:", e)
        await q.message.reply_text("Download failed ❌")
        return

    with open(path, "rb") as f:
        if mp3:
            await q.message.reply_audio(f)
        else:
            await q.message.reply_document(f)

    os.remove(path)


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang_"))
app.add_handler(CallbackQueryHandler(menu_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
app.add_handler(MessageHandler(filters.Regex(r"^/dl_"), dl_command))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
