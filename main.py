from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import os
import asyncio
import subprocess
from collections import deque

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_state = {}

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ================= QUEUE =================
download_queue = deque()
is_processing = False


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    await update.message.reply_text("اختار اللغة 🌍", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= LANGUAGE =================
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = {}

    keyboard = [
        [InlineKeyboardButton("YouTube 🎥", callback_data="yt")],
        [InlineKeyboardButton("TikTok 🎵", callback_data="tt")],
        [InlineKeyboardButton("Instagram 📸", callback_data="ig")],
        [InlineKeyboardButton("Facebook 📘", callback_data="fb")],
        [InlineKeyboardButton("Twitter/X 🐦", callback_data="tw")]
    ]

    await query.edit_message_text("اختار المنصة 📱", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= PLATFORM =================
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id]["platform"] = query.data

    await query.edit_message_text("ابعت اللينك 🔗")


# ================= MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id not in user_state:
        return

    user_state[user_id]["url"] = text

    keyboard = [
        [InlineKeyboardButton("160p", callback_data="q_160"),
         InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("480p", callback_data="q_480"),
         InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")]
    ]

    await update.message.reply_text("اختار الجودة 🎥", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= SPLIT =================
def split_video(file_path):
    parts = []
    duration = 300  # 5 دقائق لكل جزء

    for i in range(5):
        output = f"{file_path}_part{i+1}.mp4"

        subprocess.call([
            "ffmpeg",
            "-y",
            "-i", file_path,
            "-ss", str(i * duration),
            "-t", str(duration),
            output
        ])

        if os.path.exists(output):
            parts.append(output)

    return parts


# ================= MERGE =================
def merge_videos(parts, output_path):
    list_file = "parts.txt"

    with open(list_file, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.call([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ])

    os.remove(list_file)


# ================= QUEUE =================
async def process_queue():
    global is_processing

    if is_processing:
        return

    is_processing = True

    while download_queue:
        update, context, url, quality = download_queue.popleft()

        try:
            await run_download(update, context, url, quality)
        except Exception as e:
            print("ERROR:", e)

    is_processing = False


# ================= DOWNLOAD CORE =================
async def run_download(update, context, url, quality):
    query = update.callback_query

    await query.message.reply_text("⏳ جاري التحميل...")

    try:
        if quality == "mp3":
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            }
        else:
            ydl_opts = {
                "format": f"bestvideo[height<={quality}]+bestaudio/best",
                "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # ================= SPLIT =================
        if size_mb > 50 and quality != "mp3":
            parts = split_video(file_path)

            user_state[query.from_user.id]["parts"] = parts

            for p in parts:
                with open(p, "rb") as f:
                    await query.message.reply_document(f)
                os.remove(p)

            os.remove(file_path)

            await query.message.reply_text(
                "📦 تم التقسيم، هل تريد دمج الفيديو؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 دمج الفيديو", callback_data="merge")]
                ])
            )

        else:
            with open(file_path, "rb") as f:
                await query.message.reply_document(f)

            os.remove(file_path)

    except Exception as e:
        await query.message.reply_text(f"❌ خطأ:\n{e}")


# ================= QUALITY =================
async def download_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    choice = query.data
    url = user_state[user_id]["url"]

    quality = "mp3" if choice == "mp3" else choice.split("_")[1]

    download_queue.append((update, context, url, quality))

    await query.edit_message_text("📥 تم إضافة طلبك في الطابور...")

    asyncio.create_task(process_queue())


# ================= MERGE HANDLER =================
async def merge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = user_state.get(query.from_user.id, {}).get("parts")

    if not parts:
        await query.message.reply_text("❌ مفيش ملفات للدمج")
        return

    output = f"{DOWNLOAD_FOLDER}/merged.mp4"

    merge_videos(parts, output)

    with open(output, "rb") as f:
        await query.message.reply_document(f)

    os.remove(output)


# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language, pattern="lang_"))
app.add_handler(CallbackQueryHandler(platform, pattern="^(yt|tt|ig|fb|tw)$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(download_quality))
app.add_handler(CallbackQueryHandler(merge_handler, pattern="merge"))

print("Bot Running...")
app.run_polling()
