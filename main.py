import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_ID
from youtube import search_youtube
from database import add_user, inc_search, stats

logging.basicConfig(level=logging.INFO)

PLATFORMS = ["YouTube", "TikTok", "Instagram", "Facebook", "Twitter", "Other"]

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    keyboard = [
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang")]
    ]

    await update.message.reply_text(
        "🌍 Welcome / اختار اللغة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= LANG =================
async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [[InlineKeyboardButton(p, callback_data=f"platform_{p}")] for p in PLATFORMS]

    await q.edit_message_text(
        "📱 اختر المنصة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= PLATFORM =================
async def platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    p = q.data.replace("platform_", "")
    context.user_data["platform"] = p

    if p == "YouTube":
        await q.edit_message_text("🔎 ابعت اسم الفيديو أو الرابط:")
    else:
        await q.edit_message_text(f"⚡ {p} (روابط فقط حالياً)")

# ================= SEARCH =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("platform") != "YouTube":
        return

    query = update.message.text
    user_id = update.effective_user.id

    inc_search(user_id)

    await update.message.reply_text("🔎 Searching...")

    results = search_youtube(query)
    context.user_data["results"] = results

    keyboard = [
        [InlineKeyboardButton(v["title"][:40], callback_data=f"v_{i}")]
        for i, v in enumerate(results)
    ]

    await update.message.reply_text(
        "🎬 Results:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= VIDEO =================
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    idx = int(q.data.split("_")[1])
    v = context.user_data["results"][idx]

    context.user_data["video"] = v

    keyboard = [
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("1080p", callback_data="q_1080")],
        [InlineKeyboardButton("🎵 MP3 (UI)", callback_data="mp3")],
    ]

    await q.edit_message_text(
        f"""🎬 {v['title']}

👁 {v['views']}
⏱ {v['duration']}

اختار الجودة:""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= QUALITY =================
async def quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    v = context.user_data.get("video")

    if q.data == "mp3":
        await q.edit_message_text("🎵 MP3 selected (UI only)")
        return

    quality = q.data.split("_")[1]

    await q.edit_message_text(
        f"""📥 Selected: {quality}

🎬 {v['title']}

⚠️ UI mode only"""
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    s = stats()

    await update.message.reply_text(
        f"""📊 BOT STATS

👥 Users: {s['users']}
🔎 Searches: {s['searches']}"""
    )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(lang, pattern="lang"))
    app.add_handler(CallbackQueryHandler(platform, pattern="platform_"))
    app.add_handler(CallbackQueryHandler(video, pattern="v_"))
    app.add_handler(CallbackQueryHandler(quality, pattern="q_"))
    app.add_handler(CallbackQueryHandler(quality, pattern="mp3"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("PRO MAX BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
