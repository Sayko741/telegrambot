from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

user_data = {}

# ================= START (LANGUAGE SCREEN) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.clear()

    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]

    await update.message.reply_text(
        "🌍 اختار اللغة",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= LANGUAGE =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_data["lang"] = q.data

    keyboard = [
        [InlineKeyboardButton("🔍 Start", callback_data="menu_start")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")]
    ]

    await q.message.edit_text(
        "👋 ابعت اسم فيديو أو رابط 🔎",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= MENU =================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "menu_start":
        await q.message.edit_text("🔎 ابعت اسم الفيديو أو الرابط")

    elif q.data == "help":
        await q.message.edit_text(
            "📌 طريقة الاستخدام:\n"
            "- ابعت اسم فيديو 🔎\n"
            "- أو رابط 🎬\n"
            "- اختار الجودة 🎯",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Back", callback_data="back")]
            ])
        )

    elif q.data == "back":
        keyboard = [
            [InlineKeyboardButton("🔍 Start", callback_data="menu_start")],
            [InlineKeyboardButton("❓ Help", callback_data="help")],
            [InlineKeyboardButton("🔄 Restart", callback_data="restart")]
        ]

        await q.message.edit_text("🏠 Menu", reply_markup=InlineKeyboardMarkup(keyboard))

    elif q.data == "restart":
        await start(q, context)


# ================= YOUTUBE SEARCH =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    # لو رابط
    if text.startswith("http"):
        user_data[uid] = text

        keyboard = [
            [InlineKeyboardButton("1080p", callback_data="q_1080")],
            [InlineKeyboardButton("720p", callback_data="q_720")],
            [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
        ]

        await update.message.reply_text(
            "🎯 اختر الجودة",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # بحث API
    url = "https://www.googleapis.com/youtube/v3/search"

    r = requests.get(url, params={
        "part": "snippet",
        "q": text,
        "type": "video",
        "maxResults": 5,
        "key": YOUTUBE_API_KEY
    })

    data = r.json()

    message = f'📋┃نتائج البحث عن "{text}"\n\n'
    keyboard = []

    for item in data["items"]:
        vid = item["id"]["videoId"]
        title = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]

        message += f"""🎬 {title}
👤 {channel}

"""

        keyboard.append([
            InlineKeyboardButton("⬇ Download", callback_data=f"dl_{vid}")
        ])

    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= DOWNLOAD BUTTON =================
async def dl_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    vid = q.data.replace("dl_", "")
    url = f"https://www.youtube.com/watch?v={vid}"

    user_data[q.from_user.id] = url

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await q.message.reply_text(
        "🎯 اختر الجودة",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= DOWNLOAD =================
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    url = user_data.get(uid)

    mp3 = q.data == "mp3"
    quality = None if mp3 else q.data.split("_")[-1]

    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
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
        opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    await q.message.reply_text("⏳ جاري التحميل...")

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)

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
app.add_handler(CallbackQueryHandler(menu, pattern="menu_"))
app.add_handler(CallbackQueryHandler(menu, pattern="help"))
app.add_handler(CallbackQueryHandler(menu, pattern="back"))
app.add_handler(CallbackQueryHandler(menu, pattern="restart"))

app.add_handler(CallbackQueryHandler(dl_button, pattern="dl_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

print("Bot Running...")
app.run_polling()
