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
        [InlineKeyboardButton("🇪🇬 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ])


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search YouTube", callback_data="search")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")]
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
    if q.data.startswith("lang_"):
        user_state[uid] = {"mode": "menu", "results": []}
        await q.message.edit_text("🏠 Main Menu", reply_markup=main_menu())

    # HOME
    elif q.data == "home":
        user_state[uid]["mode"] = "menu"
        await q.message.edit_text("🏠 Main Menu", reply_markup=main_menu())

    # SEARCH MODE
    elif q.data == "search":
        user_state[uid]["mode"] = "search"
        await q.message.edit_text("🔎 ابعت اسم الفيديو")

    # SELECT VIDEO FROM SEARCH
    elif q.data.startswith("vid_"):
        vid = q.data.split("_")[1]
        user_state[uid]["url"] = f"https://www.youtube.com/watch?v={vid}"

        await q.message.edit_text(
            "🎯 اختر الجودة",
            reply_markup=quality_menu()
        )

    # DOWNLOAD
    elif q.data.startswith("q_") or q.data == "mp3":
        url = user_state.get(uid, {}).get("url")

        mp3 = q.data == "mp3"
        quality = None if mp3 else q.data.split("_")[1]

        await q.message.edit_text("⏳
