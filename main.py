from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import asyncio
import subprocess
from collections import deque

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_state = {}
search_results = {}

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

queue = deque()
processing = False


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🇪🇬 عربي", callback_data="lang")]]
    await update.message.reply_text("اختار اللغة 🌍", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= LANG =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = {}

    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")]
    ]

    await query.edit_message_text("اختار المنصة 📱", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= PLATFORM =================
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id]["platform"] = query.data

    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]

    await query.edit_message_text("ابعت لينك أو بحث 🔎", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= BACK =================
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await language(update, context)


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

    await update.message.reply_text("🎯 اختار:", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= SEARCH =================
async def search(update, query, data):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        result = ydl.extract_info(f"ytsearch5:{data}", download=False)

    vids = result["entries"]
    search_results[query.from_user.id] = vids

    keyboard = [[InlineKeyboardButton(v["title"][:40], callback_data=f"vid_{i}")] for i, v in enumerate(vids)]

    await query.message.reply_text("🔎 نتائج:", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= SPLIT =================
def split_video(file_path):
    parts = []
    duration = 300

    for i in range(5):
        out = f"{file_path}_part{i}.mp4"

        subprocess.call([
            "ffmpeg",
            "-y",
            "-i", file_path,
            "-ss", str(i * duration),
            "-t", str(duration),
            out
        ])

        if os.path.exists(out):
            parts.append(out)

    return parts


# ================= MERGE =================
def merge(parts, output):
    file_list = "list.txt"

    with open(file_list, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.call([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", file_list,
        "-c", "copy",
        output
    ])

    os.remove(file_list)


# ================= QUEUE =================
async def run_queue():
    global processing

    if processing:
        return

    processing = True

    while queue:
        update, context, data, quality, is_search = queue.popleft()

        try:
            await run_core(update, context, data, quality, is_search)
        except:
            pass

    processing = False


# ================= CORE =================
async def run_core(update, context, data, quality, is_search):
    query = update.callback_query

    if is_search:
        await search(update, query, data)
        return

    await query.message.reply_text("⏳ جاري التحميل...")

    opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }

    if quality == "mp3":
        opts["format"] = "bestaudio"
    else:
        opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(data, download=True)
        file_path = ydl.prepare_filename(info)

    size = os.path.getsize(file_path) / (1024 * 1024)

    # ================= SPLIT =================
    if size > 50 and quality != "mp3":
        parts = split_video(file_path)
        user_state[query.from_user.id]["parts"] = parts

        for p in parts:
            with open(p, "rb") as f:
                await query.message.reply_document(f)
            os.remove(p)

        os.remove(file_path)

        keyboard = [[InlineKeyboardButton("📦 دمج الفيديو", callback_data="merge")]]

        await query.message.reply_text("📦 تم التقسيم", reply_markup=InlineKeyboardMarkup(keyboard))

    else:
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
    is_search = not data.startswith("http")

    queue.append((update, context, data, quality, is_search))

    await query.edit_message_text("📥 في الطابور...")

    asyncio.create_task(run_queue())


# ================= SELECT VIDEO =================
async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    i = int(query.data.split("_")[1])
    vid = search_results[query.from_user.id][i]

    url = vid["webpage_url"]
    user_state[query.from_user.id]["input"] = url

    keyboard = [
        [InlineKeyboardButton("160p", callback_data="q_160"),
         InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("720p", callback_data="q_720"),
         InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await query.edit_message_text("🎬 الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= MERGE =================
async def merge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = user_state.get(query.from_user.id, {}).get("parts")

    if not parts:
        await query.message.reply_text("❌ مفيش ملفات")
        return

    out = f"{DOWNLOAD_FOLDER}/merged.mp4"
    merge(parts, out)

    with open(out, "rb") as f:
        await query.message.reply_document(f)

    os.remove(out)


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang"))
app.add_handler(CallbackQueryHandler(platform, pattern="^(yt|tt|ig)$"))
app.add_handler(CallbackQueryHandler(back, pattern="back"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(quality, pattern="^(q_|mp3)$"))
app.add_handler(CallbackQueryHandler(select_video, pattern="^vid_"))
app.add_handler(CallbackQueryHandler(merge_handler, pattern="merge"))

print("Bot Running...")
app.run_polling()
