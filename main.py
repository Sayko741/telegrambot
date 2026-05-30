from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

user_state = {}

# ================= TEXT =================
TEXT = {
    "ar": {
        "choose_lang": "اختار اللغة 🌍",
        "send": "ابعت اسم الفيديو 🔎",
        "quality": "اختار الجودة 🎯",
        "downloading": "⏳ جاري التحميل...",
        "home": "🏠 الرئيسية"
    },
    "en": {
        "choose_lang": "Choose language 🌍",
        "send": "Send video name 🔎",
        "quality": "Choose quality 🎯",
        "downloading": "⏳ Downloading...",
        "home": "🏠 Home"
    }
}

def t(uid, key):
    lang = user_state.get(uid, {}).get("lang", "ar")
    return TEXT[lang][key]


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.clear()

    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]

    await update.message.reply_text(
        TEXT["ar"]["choose_lang"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= CALLBACKS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # LANGUAGE
    if q.data.startswith("lang_"):
        lang = q.data.split("_")[1]
        user_state[uid] = {"lang": lang, "mode": "search"}

        await q.message.edit_text(t(uid, "send"))

    # HOME
    elif q.data == "home":
        user_state[uid]["mode"] = "search"
        await q.message.edit_text(t(uid, "send"))

    # VIDEO SELECT
    elif q.data.startswith("vid_"):
        vid = q.data.split("_")[1]
        user_state[uid]["url"] = f"https://www.youtube.com/watch?v={vid}"

        keyboard = [
            [InlineKeyboardButton("1080p", callback_data="q_1080")],
            [InlineKeyboardButton("720p", callback_data="q_720")],
            [InlineKeyboardButton("480p", callback_data="q_480")],
            [InlineKeyboardButton("360p", callback_data="q_360")],
            [InlineKeyboardButton("240p", callback_data="q_240")],
            [InlineKeyboardButton("144p", callback_data="q_144")],
            [InlineKeyboardButton("🎵 MP3", callback_data="mp3")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]

        await q.message.edit_text(t(uid, "quality"), reply_markup=InlineKeyboardMarkup(keyboard))


# ================= SEARCH =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if uid not in user_state:
        await update.message.reply_text("ابدأ /start")
        return

    if user_state[uid]["mode"] != "search":
        return

    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "snippet",
            "q": text,
            "type": "video",
            "maxResults": 5,
            "key": YOUTUBE_API_KEY
        })

        data = r.json()

        msg = f'📋┃نتائج البحث عن "{text}"\n\n'
        keyboard = []

        for item in data.get("items", []):
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]

            msg += (
                f"🎬 {title}\n"
                f"👤 {channel}\n"
                f"🕑 -- - 👁 --\n"
                f"🔗 /dl_{vid}\n\n"
            )

            keyboard.append([
                InlineKeyboardButton(f"🎬 {title[:22]}", callback_data=f"vid_{vid}")
            ])

        keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="home")])

        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        print("SEARCH ERROR:", e)
        await update.message.reply_text("❌ Search failed")


# ================= DOWNLOAD =================
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    url = user_state.get(uid, {}).get("url")

    if not url:
        await q.message.reply_text("❌ مفيش فيديو مختار")
        return

    await q.message.edit_text(t(uid, "downloading"))

    mp3 = q.data == "mp3"
    quality = None if mp3 else q.data.split("_")[1]

    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    if mp3:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

        with open(path, "rb") as f:
            if mp3:
                await q.message.reply_audio(f)
            else:
                await q.message.reply_document(f)

        os.remove(path)

    except Exception as e:
        print("ERROR:", e)
        await q.message.reply_text("❌ فشل التحميل")


# ================= RUN =================
os.makedirs("downloads", exist_ok=True)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons, pattern="lang_|vid_|home"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("Bot Running...")
app.run_polling()
