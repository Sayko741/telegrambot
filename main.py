from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

user_state = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.clear()

    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang")]
    ]

    await update.message.reply_text(
        "🌍 اختر اللغة",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= CALLBACKS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # LANGUAGE
    if q.data == "lang":
        user_state[uid] = {"mode": "search"}
        await q.message.edit_text("🔎 ابعت اسم الفيديو")

    # SELECT VIDEO
    elif q.data.startswith("vid_"):
        vid = q.data.split("_")[1]
        user_state[uid]["url"] = f"https://www.youtube.com/watch?v={vid}"

        keyboard = [
            [InlineKeyboardButton("🎬 MP4", callback_data="dl_mp4")],
            [InlineKeyboardButton("🎵 MP3", callback_data="dl_mp3")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]

        await q.message.edit_text(
            "🎯 اختر التحميل",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # HOME
    elif q.data == "home":
        await q.message.edit_text("🏠 Home")


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
                InlineKeyboardButton(f"⬇ {title[:22]}", callback_data=f"vid_{vid}")
            ])

        keyboard.append([
            InlineKeyboardButton("🏠 Home", callback_data="home")
        ])

        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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

    await q.message.edit_text("⏳ جاري التحميل...")

    mp3 = q.data == "dl_mp3"

    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    # ================= MP3 (FFMPEG REQUIRED) =================
    if mp3:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["format"] = "best"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

        if not os.path.exists(path):
            raise Exception("file not found")

        with open(path, "rb") as f:
            if mp3:
                await q.message.reply_audio(f)
            else:
                await q.message.reply_document(f)

        os.remove(path)

    except Exception as e:
        print("DOWNLOAD ERROR:", e)
        await q.message.reply_text("❌ فشل التحميل")


# ================= APP =================
os.makedirs("downloads", exist_ok=True)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(CallbackQueryHandler(download, pattern="dl_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("Bot Running...")
app.run_polling()
