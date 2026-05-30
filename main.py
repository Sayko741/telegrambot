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

# ================= USER STATE =================
user_state = {}

# ================= AI =================
async def ai_reply(text):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "انت مساعد داخل بوت تيليجرام وترد بشكل بسيط."},
                {"role": "user", "content": text}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        return "❌ AI مش شغال حالياً"


# ================= MAIN MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search YouTube", callback_data="search_mode")],
        [InlineKeyboardButton("🤖 AI Chat", callback_data="ai_mode")]
    ])


def back_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data="home")]
    ])


def quality_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")],
        [InlineKeyboardButton("⬅ Back", callback_data="home")]
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.clear()

    await update.message.reply_text(
        "🌍 Welcome\n\nاختر من القائمة:",
        reply_markup=main_menu()
    )


# ================= BUTTON HANDLER =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # HOME
    if q.data == "home":
        user_state[uid] = {"mode": "menu"}
        await q.message.edit_text("🏠 Main Menu", reply_markup=main_menu())

    # SEARCH MODE
    elif q.data == "search_mode":
        user_state[uid] = {"mode": "search"}
        await q.message.edit_text("🔎 ابعت اسم الفيديو")

    # AI MODE
    elif q.data == "ai_mode":
        user_state[uid] = {"mode": "ai"}
        await q.message.edit_text("🤖 ابعت سؤالك")

    # DOWNLOAD QUALITY
    elif q.data.startswith("q_") or q.data == "mp3":
        url = user_state.get(uid, {}).get("url")

        mp3 = q.data == "mp3"
        quality = None if mp3 else q.data.split("_")[1]

        await q.message.edit_text("⏳ جاري التحميل...")

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

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

        with open(path, "rb") as f:
            if mp3:
                await q.message.reply_audio(f)
            else:
                await q.message.reply_document(f)

        os.remove(path)


# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if uid not in user_state:
        user_state[uid] = {"mode": "menu"}
        await update.message.reply_text("🏠 Main Menu", reply_markup=main_menu())
        return

    mode = user_state[uid]["mode"]

    # ================= AI MODE =================
    if mode == "ai":
        reply = await ai_reply(text)
        await update.message.reply_text(reply, reply_markup=back_home())
        return

    # ================= LINK =================
    if text.startswith("http"):
        user_state[uid]["url"] = text
        await update.message.reply_text("🎯 اختر الجودة", reply_markup=quality_menu())
        return

    # ================= SEARCH MODE =================
    if mode == "search":

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

            await update.message.reply_text(message, reply_markup=back_home())

        except Exception as e:
            print(e)
            await update.message.reply_text("Search error ❌")


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("Bot Running...")
app.run_polling()
