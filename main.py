from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

user_state = {}

# ================= MENUS =================
def lang_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang")]
    ])


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search YouTube", callback_data="search")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")]
    ])


def quality_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")]
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.clear()
    await update.message.reply_text("🌍 اختر اللغة", reply_markup=lang_menu())


# ================= CALLBACKS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # LANGUAGE
    if q.data == "lang":
        user_state[uid] = {"mode": "menu"}
        await q.message.edit_text("🏠 Main Menu", reply_markup=main_menu())

    # HOME
    elif q.data == "home":
        user_state[uid]["mode"] = "menu"
        await q.message.edit_text("🏠 Main Menu", reply_markup=main_menu())

    # SEARCH MODE
    elif q.data == "search":
        user_state[uid]["mode"] = "search"
        await q.message.edit_text("🔎 ابعت اسم الفيديو")

    # SELECT VIDEO
    elif q.data.startswith("vid_"):
        vid = q.data.split("_")[1]
        user_state[uid]["url"] = f"https://www.youtube.com/watch?v={vid}"

        await q.message.edit_text("🎯 اختر الجودة", reply_markup=quality_menu())

    # DOWNLOAD
    elif q.data.startswith("q_") or q.data == "mp3":
        url = user_state.get(uid, {}).get("url")

        if not url:
            await q.message.edit_text("❌ مفيش فيديو مختار", reply_markup=main_menu())
            return

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
            print("DOWNLOAD ERROR:", e)
            await q.message.reply_text("❌ فشل التحميل")


# ================= MESSAGE =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if uid not in user_state:
        await update.message.reply_text("🌍 ابدأ بـ /start", reply_markup=lang_menu())
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

        for i in data.get("items", []):
            vid = i["id"]["videoId"]
            title = i["snippet"]["title"]
            channel = i["snippet"]["channelTitle"]

            msg += f"""🎬 {title}
👤 {channel}
🔗 /dl_{vid}

"""

            keyboard.append([
                InlineKeyboardButton(f"⬇ {title[:20]}", callback_data=f"vid_{vid}")
            ])

        keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="home")])

        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print("SEARCH ERROR:", e)
        await update.message.reply_text("❌ Search failed")


# ================= APP =================
os.makedirs("downloads", exist_ok=True)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

print("Bot Running...")
app.run_polling()
