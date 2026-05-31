#!/usr/bin/env python3
"""Telegram Bot"""

import os
import subprocess
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== STATE ====================
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {'lang': None, 'url': None}
    return users[uid]

# ==================== MESSAGES ====================
MSG = {
    'ar': {'welcome': 'مرحباً! اختر:', 'selected': '✅ تم', 'main': '📎 أرسل رابط أو ابحث:', 'down': '⏳ جاري...', 'done': '✅ تم!', 'error': '❌ خطأ', 'no': '❌ لا نتائج', 'search': '⏳...', 'select': '🎬:'},
    'en': {'welcome': 'Hello! Choose:', 'selected': '✅ Done', 'main': '📎 Link or search:', 'down': '⏳...', 'done': '✅ Done!', 'error': '❌ Error', 'no': '❌ No results', 'search': '⏳...', 'select': '🎬:'}
}

# ==================== KEYBOARDS ====================
def lang_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🇸🇦 العربية', callback_data='la')],
        [InlineKeyboardButton('🇬🇧 English', callback_data='le')]
    ])

def dl_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📥 Video', callback_data='dl_video')],
        [InlineKeyboardButton('🎵 MP3', callback_data='dl_mp3')]
    ])

# ==================== DOWNLOAD ====================
def download_file(url, mp3=False):
    folder = '/tmp'
    os.makedirs(folder, exist_ok=True)
    
    try:
        if mp3:
            cmd = ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', f'{folder}/%(title)s.%(ext)s', url]
        else:
            cmd = ['yt-dlp', '-f', 'best', '-o', f'{folder}/%(title)s.%(ext)s', url]
        
        logger.info(f'Command: {cmd}')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f'Error: {result.stderr}')
            return None
        
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                return path
        
        return None
    except Exception as e:
        logger.error(f'Download error: {e}')
        return None

# ==================== SEARCH ====================
def search_videos(query):
    try:
        cmd = ['yt-dlp', '--print', '%(title)s|%(uploader)s|%(id)s', f'ytsearch10:{query}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return []
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    videos.append({
                        'title': parts[0][:40],
                        'channel': parts[1],
                        'video_id': parts[2]
                    })
        return videos[:8]
    except Exception as e:
        logger.error(f'Search error: {e}')
        return []

# ==================== HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    
    if user['lang'] is None:
        await update.message.reply_text(MSG['ar']['welcome'], reply_markup=lang_keyboard())
    else:
        await update.message.reply_text(MSG[user['lang']]['main'])

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    user['lang'] = 'ar' if query.data == 'la' else 'en'
    
    await query.edit_message_text(MSG[user['lang']]['selected'])
    await query.message.reply_text(MSG[user['lang']]['main'])

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lang = user.get('lang', 'en')
    text = update.message.text
    
    is_link = 'http' in text.lower() or 'www' in text.lower() or '.com' in text.lower() or '.be' in text.lower()
    
    if is_link:
        await update.message.reply_text(MSG[lang]['down'])
        
        file_path = download_file(text, mp3=False)
        
        if file_path and os.path.exists(file_path):
            try:
                await update.message.reply_video(open(file_path, 'rb'))
                os.remove(file_path)
                await update.message.reply_text(MSG[lang]['done'])
            except Exception as e:
                logger.error(f'Send error: {e}')
                await update.message.reply_text(MSG[lang]['error'])
        else:
            await update.message.reply_text(MSG[lang]['error'])
    else:
        await update.message.reply_text(MSG[lang]['search'])
        
        results = search_videos(text)
        
        if not results:
            await update.message.reply_text(MSG[lang]['no'])
            return
        
        message_text = f'📋┃"{text}"\n\n'
        buttons = []
        
        for i, video in enumerate(results, 1):
            message_text += f"{i}️⃣ {video['title']}\n"
            message_text += f"   👤 {video['channel']}\n\n"
            buttons.append([InlineKeyboardButton(f"▶️ {i}", callback_data=f"vid_{video['video_id']}")])
        
        await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(buttons))

async def video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    lang = user.get('lang', 'en')
    
    video_id = query.data.replace('vid_', '')
    user['url'] = f'https://www.youtube.com/watch?v={video_id}'
    
    await query.edit_message_text(MSG[lang]['select'], reply_markup=dl_keyboard())

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    lang = user.get('lang', 'en')
    
    mp3 = (query.data == 'dl_mp3')
    url = user.get('url')
    
    if not url:
        await query.message.reply_text(MSG[lang]['error'])
        return
    
    await query.edit_message_text(MSG[lang]['down'])
    
    file_path = download_file(url, mp3=mp3)
    
    if file_path and os.path.exists(file_path):
        try:
            if mp3:
                await query.message.reply_audio(open(file_path, 'rb'))
            else:
                await query.message.reply_video(open(file_path, 'rb'))
            os.remove(file_path)
            await query.message.reply_text(MSG[lang]['done'])
        except Exception as e:
            logger.error(f'Send error: {e}')
            await query.message.reply_text(MSG[lang]['error'])
    else:
        await query.message.reply_text(MSG[lang]['error'])

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Error: {context.error}')

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern='^l[ae]$'))
    app.add_handler(CallbackQueryHandler(video_callback, pattern='^vid_'))
    app.add_handler(CallbackQueryHandler(download_callback, pattern='^dl_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)
    
    print('🤖 Bot running')
    app.run_polling()

if __name__ == '__main__':
    main()
