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

user_state = {}

# ================= AI =================
async def ai_reply(text):
    try:
        print("AI REQUEST:", text)

        if not OPENAI_API_KEY:
            return "❌ مفتاح الـ AI مش متحط"

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "انت مساعد ذكي داخل بوت تيليجرام وترد بشكل بسيط."},
                {"role": "user", "content": text}
            ]
        )

        answer = res.choices[0].message.content
        print("AI RESPONSE:", answer)
        return answer

    except Exception as e:
        print("AI ERROR:", str(e))
        return "❌ في مشكلة في الـ AI (راجع Logs)"


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.clear()

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

    user_state[q.from_user.id] = {"mode": "menu"}

    await q.message.edit_text("👋 ابعت اسم فيديو أو اسألني 🤖")


# ================= SEARCH + AI =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    # ================= LINK =================
    if text.startswith("http"):
        user_state[uid] = {"url": text}

        await update.message.reply_text(
            "🎯 اختر الجودة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1080p", callback_data="q_1080")],
                [InlineKeyboardButton("720p", callback_data="q_720")],
                [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
            ])
        )
        return

    # ================= AI (fallback لو مفيش بحث) =================
    if len(text.split()) <= 2:
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

        message = f'📋┃نتائج البحث عن "{text}"\n\n'

        for item in data["items"]:
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]

            message += f"""🎬 {title}
👤 {channel}
🔗 /dl_{vid}

"""

        await update.message.reply_text(message)

    except Exception as e:
        print("SEARCH ERROR:", e)
        await update.message.reply_text("Search failed ❌")


# ================= DOWNLOAD =================
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    url = user_state.get(uid, {}).get("url")

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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
app.add_handler(CallbackQueryHandler(download, pattern="q_|mp3"))

print("Bot Running...")
app.run_polling()
