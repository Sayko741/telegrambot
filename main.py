#!/usr/bin/env python3
"""Telegram Bot - Simple"""

import os
import subprocess
import shutil
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {'lang': None, 'url': None}
    return users[uid]

MSG = {
    'ar': {'w': 'مرحباً! اختر:', 's': '✅', 'm': '📎 أرسل رابط أو ابحث:', 'd': '⏳...', 'ok': '✅', 'e': '❌', 'n': '❌', 'x': '⏳', 'p': '🎬'},
    'en': {'w': 'Hello! Choose:', 's': '✅', 'm': '📎 Link or search:', 'd': '⏳...', 'ok': '✅', 'e': '❌', 'n': '❌', 'x': '⏳', 'p': '🎬'}
}

def kb_l():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🇸🇦 العربية', callback_data='la')],
        [InlineKeyboardButton('🇬🇧 English', callback_data='le')]
    ])

def kb_dl():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📥 Video', callback_data='dv')],
        [InlineKeyboardButton('🎵 MP3', callback_data='dm')]
    ])

def download_video(url, to_mp3=False):
    folder = '/tmp'
    os.makedirs(folder, exist_ok=True)
    
    try:
        if to_mp3:
            # Use simplest MP3 command
            cmd = ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', f'{folder}/out.%(ext)s', '--no-progress', url]
        else:
            # Best video
            cmd = ['yt-dlp', '-f', 'best', '-o', f'{folder}/out.%(ext)s', '--no-progress', url]
        
        logger.info(f'Running: {cmd}')
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        logger.info(f'Result: {result.returncode}')
        if result.stderr:
            logger.info(f'Stderr: {result.stderr}')
        
        # Find file
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isfile(path) and not f.startswith('.'):
                logger.info(f'Found: {path}')
                return path
        
        return None
        
    except Exception as e:
        logger.error(f'Error: {e}')
        return None

def search_youtube(query):
    try:
        # Simple search using yt-dlp
        cmd = ['yt-dlp', f'ytsearch10:{query}', '--skip-download', '--no-warnings', '-J']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f'Search error: {result.stderr}')
            return []
        
        # Parse JSON output
        import json
        try:
            data = json.loads(result.stdout)
            entries = data.get('entries', [])
            
            videos = []
            for e in entries[:8]:
                videos.append({
                    'title': e.get('title', 'Unknown')[:40],
                    'channel': e.get('uploader', 'Unknown'),
                    'video_id': e.get('id', '')
                })
            return videos
        except:
            return []
            
    except Exception as e:
        logger.error(f'Search error: {e}')
        return []

async def start(update, context):
    u = get_user(update.effective_user.id)
    if u['lang'] is None:
        await update.message.reply_text(MSG['ar']['w'], reply_markup=kb_l())
    else:
        await update.message.reply_text(MSG[u['lang']]['m'])

async def lang_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    u['lang'] = 'ar' if q.data == 'la' else 'en'
    await q.edit_message_text(MSG[u['lang']]['s'])
    await q.message.reply_text(MSG[u['lang']]['m'])

async def msg_h(update, context):
    u = get_user(update.effective_user.id)
    l = u.get('lang', 'en')
    txt = update.message.text
    
    is_link = 'http' in txt.lower() or 'www' in txt.lower()
    
    if is_link:
        await update.message.reply_text(MSG[l]['d'])
        
        f = download_video(txt, to_mp3=False)
        
        if f and os.path.exists(f):
            try:
                await update.message.reply_video(open(f, 'rb'))
                os.remove(f)
                await update.message.reply_text(MSG[l]['ok'])
            except:
                await update.message.reply_text(MSG[l]['e'])
        else:
            await update.message.reply_text(MSG[l]['e'])
    else:
        await update.message.reply_text(MSG[l]['x'])
        
        r = search_youtube(txt)
        
        if not r:
            await update.message.reply_text(MSG[l]['n'])
            return
        
        txt_msg = f'📋┃"{txt}"\n\n'
        btns = []
        for i, v in enumerate(r, 1):
            txt_msg += f"{i}️⃣ {v['title']}\n👤 {v['channel']}\n\n"
            btns.append([InlineKeyboardButton(f"▶️ {i}", callback_data=f"v_{v['video_id']}")])
        
        await update.message.reply_text(txt_msg, reply_markup=InlineKeyboardMarkup(btns))

async def vid_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    l = u.get('lang', 'en')
    
    vid = q.data.replace('v_', '')
    u['url'] = f'https://youtube.com/watch?v={vid}'
    
    await q.edit_message_text(MSG[l]['p'], reply_markup=kb_dl())

async def dl_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    l = u.get('lang', 'en')
    
    mp3 = (q.data == 'dm')
    url = u.get('url')
    
    if not url:
        await q.message.reply_text(MSG[l]['e'])
        return
    
    await q.edit_message_text(MSG[l]['d'])
    
    f = download_video(url, to_mp3=mp3)
    
    if f and os.path.exists(f):
        try:
            if mp3:
                await q.message.reply_audio(open(f, 'rb'))
            else:
                await q.message.reply_video(open(f, 'rb'))
            os.remove(f)
            await q.message.reply_text(MSG[l]['ok'])
        except:
            await q.message.reply_text(MSG[l]['e'])
    else:
        await q.message.reply_text(MSG[l]['e'])

async def err(update, context):
    logger.error(f'Error: {context.error}')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(lang_cb, pattern='^l[ae]$'))
    app.add_handler(CallbackQueryHandler(vid_cb, pattern='^v_'))
    app.add_handler(CallbackQueryHandler(dl_cb, pattern='^d[vm]$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    app.add_error_handler(err)
    print('Running')
    app.run_polling()

if __name__ == '__main__':
    main()
