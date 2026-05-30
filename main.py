from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 ابعت رابط فيديو أو اسم فيديو للبحث")


# ================= SEARCH =================
async def search_youtube(query):
    import requests

    r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 5,
        "key": os.getenv("YOUTUBE_API_KEY")
    })

    data = r.json()
    results = []

    for item in data.get("items", []):
        vid = item["id"]["videoId"]
        title = item["snippet"]["title"]
        results.append((vid, title))

    return results


# ================= MESSAGE HANDLER =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    # لو رابط
    if text.startswith("http"):
        user_data[uid] = {"url": text}

        keyboard = [
            [InlineKeyboardButton("1080p", callback_data="q_1080")],
            [InlineKeyboardButton("720p", callback_data="q_720")],
            [InlineKeyboardButton("480p", callback_data="q_480")],
            [InlineKeyboardButton("360p", callback_data="q_360")],
            [InlineKeyboardButton("144p", callback_data="q_144")],
            [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
        ]

        await update.message.reply_text(
            "🎯 اختر الجودة",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # لو بحث
    results = await search_youtube(text)

    msg = f'📋┃نتائج البحث عن "{text}"\n\n'
    keyboard = []

    for vid, title in results:
        msg += f"🎬 {title}\n🔗 /v_{vid}\n\n"

        keyboard.append([
            InlineKeyboardButton(title[:25], callback_data=f"vid_{vid}")
        ])

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


# ================= VIDEO SELECT =================
async def video_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    vid = q.data.split("_")[1]

    user_data[uid] = {"url": f"https://www.youtube.com/watch?v={vid}"}

    keyboard = [
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("144p", callback_data="q_144")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await q.message.edit_text("🎯 اختر الجودة", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= DOWNLOAD =================
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    url = user_data.get(uid, {}).get("url")

    if not url:
        await q.message.reply_text("❌ مفيش رابط")
        return

    await q.message.edit_text("⏳ جاري التحميل...")

    mp3 = q.data == "mp3"
    quality = None if mp3 else q.data.split("_")[1]

    opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    # ================= MP3 =================
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
        await q.message.reply_text("❌ الفيديو ده مش مدعوم أو حصل خطأ")



# ================= RUN =================
os.makedirs("downloads", exist_ok=True)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(video_select, pattern="vid_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
