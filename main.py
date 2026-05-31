#!/usr/bin/env python3
"""
Telegram Bot - Download videos from any platform
"""

import os
import asyncio
import logging
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATA ====================
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {'lang': None, 'url': None}
    return users[uid]

# Messages
TXT = {
    'ar': {'wel': 'مرحباً! اختر:', 'ok': '✅ تم', 'menu': '📎 أرسل رابط أو ابحث:', 'dl': '⏳ جاري...', 'err': '❌ خطأ', 'no': '❌ لا', 'sr': '⏳', 'sel': '🎬 اختار:'},
    'en': {'wel': 'Hello! Choose:', 'ok': '✅ Done', 'menu': '📎 Link or search:', 'dl': '⏳ Downloading...', 'err': '❌ Error', 'no': '❌ No', 'sr': '⏳', 'sel': '🎬 Select:'}
}

def kb_lang():
    return InlineKeyboardMarkup([[InlineKeyboardButton('🇸🇦 العربية', callback_data='la'), InlineKeyboardButton('🇬🇧 English', callback_data='le')]])

def kb_dl():
    return InlineKeyboardMarkup([[InlineKeyboardButton('📥 Video', callback_data='dv')], [InlineKeyboardButton('🎵 MP3', callback_data='dm')]])

# ==================== DOWNLOAD ====================
def download_video(url, to_mp3=False):
    """Download using subprocess - more reliable"""
    folder = '/tmp'
    os.makedirs(folder, exist_ok=True)
    
    try:
        cmd = ['yt-dlp', '-f', 'best']
        
        if to_mp3:
            cmd = ['yt-dlp', '-x', '--audio-format', 'mp3']
        
        cmd.extend(['-o', f'{folder}/%(title)s.%(ext)s', url])
        
        logger.info(f'Running: {" ".join(cmd)}')
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f'yt-dlp error: {result.stderr}')
            return None
        
        # Find downloaded file
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                return path
        
        return None
        
    except Exception as e:
        logger.error(f'Download error: {e}')
        return None

# ==================== SEARCH ====================
def search_video(query):
    """Search YouTube"""
    try:
        cmd = ['yt-dlp', '--print', '%(title)s|%(uploader)s|%(id)s|%(duration)s', f'ytsearch10:{query}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return []
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    videos.append({
                        'title': parts[0][:45],
                        'channel': parts[1],
                        'id': parts[2] if len(parts) > 2 else '',
                        'dur': parts[3] if len(parts) > 3 else '0'
                    })
        return videos[:8]
        
    except Exception as e:
        logger.error(f'Search error: {e}')
        return []

# ==================== HANDLERS ====================
async def start(update, context):
    u = get_user(update.effective_user.id)
    await update.message.reply_text(
        TXT['ar']['wel'] if not u['lang'] else TXT[u['lang']]['menu'],
        reply_markup=kb_lang() if not u['lang'] else None
    )

async def lang_c(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    u['lang'] = 'ar' if q.data == 'la' else 'en'
    await q.edit_message_text(TXT[u['lang']]['ok'])
    await q.message.reply_text(TXT[u['lang']]['menu'])

async def msg_h(update, context):
    u = get_user(update.effective_user.id)
    lang = u.get('lang', 'en')
    txt = update.message.text
    
    # Check if link
    is_link = 'http' in txt.lower() or 'www' in txt.lower()
    
    if is_link:
        await update.message.reply_text(TXT[lang]['dl'])
        
        f = download_video(txt, to_mp3=False)
        
        if f and os.path.exists(f):
            await update.message.reply_video(open(f, 'rb'))
            os.remove(f)
            await update.message.reply_text(TXT[lang]['ok'])
        else:
            await update.message.reply_text(TXT[lang]['err'])
    else:
        await update.message.reply_text(TXT[lang]['sr'])
        
        r = search_video(txt)
        
        if not r:
            await update.message.reply_text(TXT[lang]['no'])
            return
        
        msg = f'📋┃"{txt}"\n\n'
        btns = []
        for i, v in enumerate(r, 1):
            msg += f"{i}️⃣ {v['title']}\n👤 {v['channel']}\n\n"
            btns.append([InlineKeyboardButton(f"▶️ {i}", callback_data=f"v_{v['id']}")])
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns))

async def vid_c(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    lang = u.get('lang', 'en')
    
    vid = q.data.replace('v_', '')
    u['url'] = f'https://youtube.com/watch?v={vid}'
    
    await q.edit_message_text(TXT[lang]['sel'], reply_markup=kb_dl())

async def dwn_c(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    lang = u.get('lang', 'en')
    
    mp3 = (q.data == 'dm')
    
    if not u.get('url'):
        await q.message.reply_text(TXT[lang]['err'])
        return
    
    await q.edit_message_text(TXT[lang]['dl'])
    
    f = download_video(u['url'], to_mp3=mp3)
    
    if f and os.path.exists(f):
        if mp3:
            await q.message.reply_audio(open(f, 'rb'))
        else:
            await q.message.reply_video(open(f, 'rb'))
        os.remove(f)
        await q.message.reply_text(TXT[lang]['ok'])
    else:
        await q.message.reply_text(TXT[lang]['err'])

async def error(update, context):
    logger.error(f'Error: {context.error}')

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(lang_c, pattern='^l[ae]$'))
    app.add_handler(CallbackQueryHandler(vid_c, pattern='^v_'))
    app.add_handler(CallbackQueryHandler(dwn_c, pattern='^d[vm]$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    app.add_error_handler(error)
    
    print('🤖 Bot running...')
    app.run_polling()

if __name__ == '__main__':
    main()
