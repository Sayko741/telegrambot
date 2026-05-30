from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

user_data = {}

# ================= AI =================
async def ai_reply(text):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "انت مساعد داخل بوت تيليجرام وترد باختصار."},
                {"role": "user", "content": text}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        return "مش قادر أرد دلوقتي ❌"


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.clear()
    await update.message.reply_text("👋 ابعت اسم فيديو أو اسألني 💬")


# ================= AI BUTTON =================
async def ai_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_data[q.from_user.id] = "ai_mode"

    await q.message.reply_text("🤖 ابعت سؤالك وأنا هرد عليك")


# ================= SEARCH =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    # ================= LINK =================
    if text.startswith("http"):
        user_data[uid] = text

        await update.message.reply_text(
            "🎯 اختر الجودة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1080p", callback_data="q_1080")],
                [InlineKeyboardButton("720p", callback_data="q_720")],
                [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
            ])
        )
        return

    # ================= AI MODE =================
    if user_data.get(uid) == "ai_mode":
        reply = await ai_reply(text)
        await update.message.reply_text(reply)
        return

    # ================= YOUTUBE SEARCH =================
    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "snippet",
            "q": text,
            "type": "video",
            "maxResults": 5,
            "key": YOUTUBE_API_KEY
        })

        data = r.json()

        message = f'📋┃**نتائج البحث** عن "**{text}**"\n\n'
        keyboard = []

        for item in data["items"]:
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]

            message += f"""🎬 [{title}](https://youtu.be/{vid})
👤 {channel}
🔗 /dl_{vid}

"""

        keyboard = [
            [InlineKeyboardButton("🤖 Talk with AI", callback_data="ai_start")]
        ]

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print("SEARCH ERROR:", e)
        await update.message.reply_text("Search failed ❌")


# ================= DOWNLOAD BUTTON =================
async def dl_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    vid = q.data.replace("dl_", "")
    url = f"https://www.youtube.com/watch?v={vid}"

    user_data[q.from_user.id] = url

    await q.message.reply_text(
        "🎯 اختر الجودة",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1080p", callback_data="q_1080")],
            [InlineKeyboardButton("720p", callback_data="q_720")],
            [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
        ])
    )


# ================= DOWNLOAD =================
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    url = user_data.get(uid)

    mp3 = q.data == "mp3"
    quality = None if mp3 else q.data.split("_")[1]

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


# ================= HANDLERS =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(ai_button, pattern="ai_start"))
app.add_handler(CallbackQueryHandler(dl_button, pattern="dl_"))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

print("Bot Running...")
app.run_polling()
