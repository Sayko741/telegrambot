from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import asyncio
from collections import deque

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_state = {}

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ================= QUEUE =================
queue = deque()
processing = False


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text("اختار اللغة 🌍", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= LANG =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = {"mode": None}

    await show_platforms(query)


# ================= SHOW PLATFORMS =================
async def show_platforms(query):
    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")],
        [InlineKeyboardButton("Facebook 📘", callback_data="fb")],
        [InlineKeyboardButton("Twitter/X 🐦", callback_data="tw")]
    ]

    await query.edit_message_text(
        "اختار المنصة 📱",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= PLATFORM =================
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id]["platform"] = query.data

    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_platform")]
    ]

    await query.edit_message_text(
        "ابعت اللينك أو كلمة بحث 🔎",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= BACK BUTTON =================
async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await show_platforms(query)


# ================= MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id not in user_state:
        return

    user_state[user_id]["input"] = text

    keyboard = [
        [InlineKeyboardButton("160p", callback_data="q_160"),
         InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("480p", callback_data="q_480"),
         InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text(
        "اختار العملية 🎥",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= QUEUE RUNNER =================
async def run_queue():
    global processing

    if processing:
        return

    processing = True

    while queue:
        update, context, data, quality = queue.popleft()

        try:
            await download_core(update, context, data, quality)
        except:
            pass

    processing = False


# ================= CORE =================
async def download_core(update, context, data, quality):
    query = update.callback_query

    await query.message.reply_text("⏳ جاري التنفيذ...")

    is_search = user_state[query.from_user.id]["platform"] == "yt" and not data.startswith("http")

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
    }

    # ================= YOUTUBE SEARCH =================
    if is_search:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            result = ydl.extract_info(f"ytsearch5:{data}", download=False)

        for v in result["entries"]:
            await query.message.reply_text(f"{v['title']}\n{v['webpage_url']}")

        return

    # ================= DOWNLOAD =================
    if quality == "mp3":
        ydl_opts["format"] = "bestaudio"
    else:
        ydl_opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"

    # cookies fix (اختياري لو عايز تحط cookies.txt)
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(data, download=True)
        file_path = ydl.prepare_filename(info)

    with open(file_path, "rb") as f:
        await query.message.reply_document(f)

    os.remove(file_path)


# ================= QUALITY =================
async def quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = user_state[user_id]["input"]
    choice = query.data

    quality = "mp3" if choice == "mp3" else choice.split("_")[1]

    queue.append((update, context, data, quality))

    await query.edit_message_text("📥 تم إضافة طلبك في الطابور")

    asyncio.create_task(run_queue())


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang_"))
app.add_handler(CallbackQueryHandler(platform, pattern="^(yt|tt|ig|fb|tw)$"))
app.add_handler(CallbackQueryHandler(back_handler, pattern="back_platform"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(quality))

print("Bot Running...")
app.run_polling()
