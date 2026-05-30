from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import requests
import google.generativeai as genai

# ================= KEYS =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= GEMINI SETUP =================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ================= STATE =================
user_state = {}

# ================= AI =================
async def ai_reply(text):
    try:
        if not GEMINI_API_KEY:
            return "❌ GEMINI API KEY مش موجود"

        response = model.generate_content(text)
        return response.text

    except Exception as e:
        print("GEMINI ERROR:", e)
        return "❌ AI مش شغال حالياً"


# ================= MENUS =================
def lang_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ])


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search YouTube", callback_data="search")],
        [InlineKeyboardButton("🤖 AI Chat", callback_data="ai")]
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


# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # LANGUAGE
    if q.data.startswith("lang_"):
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

    # AI MODE
    elif q.data == "ai":
        user_state[uid]["mode"] = "ai"
        await q.message.edit_text("🤖 ابعت سؤالك")

    # DOWNLOAD
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


# ================= MESSAGES =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if uid not in user_state:
        await update.message.reply_text("🌍 اختار اللغة الأول", reply_markup=lang_menu())
        return

    mode = user_state[uid]["mode"]

    # ================= AI =================
    if mode == "ai":
        reply = await ai_reply(text)
        await update.message.reply_text(reply)
        return

    # ================= LINK =================
    if text.startswith("http"):
        user_state[uid]["url"] = text
        await update.message.reply_text("🎯 اختر الجودة", reply_markup=quality_menu())
        return

    # ================= SEARCH =================
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

            msg
