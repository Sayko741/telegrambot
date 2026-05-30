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
        "send": "ابعت اسم الفيديو 🔎 أو رابط",
        "quality": "🎯 اختر الجودة",
        "downloading": "⏳ جاري التحميل...",
        "fail": "❌ فشل التحميل"
    },
    "en": {
        "choose_lang": "Choose language 🌍",
        "send": "Send video name or link 🔎",
        "quality": "Choose quality 🎯",
        "downloading": "⏳ Downloading...",
        "fail": "Download failed ❌"
    }
}

def t(uid, key):
    return TEXT[user_state.get(uid, {}).get("lang", "ar")][key]


# ================= START + LANGUAGE =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]

    await update.message.reply_text(
        TEXT["ar"]["choose_lang"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data.startswith("lang_"):
        lang = q.data.split("_")[1]
        user_state[uid] = {"lang": lang}

        await q.message.edit_text(t(uid, "send"))

    elif q.data.startswith("vid_"):
        vid = q.data.split("_")[1]
        user_state[uid]["url"] = f"https://www.youtube.com/watch?v={vid}"

        keyboard = quality_keyboard()
        await q.message.edit_text(t(uid, "quality"), reply_markup=keyboard)

    elif q.data.startswith("q_") or q.data == "mp3":
        await download_video(q, uid)


# ================= KEYBOARD =================
def quality_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("144p", callback_data="q_144")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ])


# ================= SEARCH =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if uid not in user_state:
        user_state[uid] = {"lang": "ar"}

    if text.startswith("http"):
        user_state[uid]["url"] = text
        await update.message.reply_text(
            t(uid, "quality"),
            reply_markup=quality_keyboard()
        )
        return

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

        msg += f"🎬 {title}\n👤 {channel}\n🔗 /dl_{vid}\n\n"

        keyboard.append([
            InlineKeyboardButton(title[:25], callback_data=f"vid_{vid}")
        ])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


# ================= DOWNLOAD (FIXED) =================
async def download_video(q, uid):
    url = user_state.get(uid, {}).get("url")

    if not url:
        await q.message.reply_text("❌ مفيش رابط")
        return

    await q.message.edit_text(t(uid, "downloading"))

    mp3 = q.data == "mp3"
    quality = None if mp3 else q.data.split("_")[1]

    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "format": "best[ext=mp4]/best"
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

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

        if mp3:
            path = path.rsplit(".", 1)[0] + ".mp3"

        with open(path, "rb") as f:
            if mp3:
                await q.message.reply_audio(f)
            else:
                await q.message.reply_document(f)

        os.remove(path)

    except Exception as e:
        print("ERROR:", e)
        await q.message.reply_text(t(uid, "fail"))


# ================= RUN =================
os.makedirs("downloads", exist_ok=True)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot Running...")
app.run_polling()
