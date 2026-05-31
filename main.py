#!/usr/bin/env python3
"""Telegram Bot - Download from any platform"""

import os
import subprocess
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== STATE ====================
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {'lang': None, 'url': None, 'action': None}
    return users[uid]

# ==================== MESSAGES ====================
MSG = {
    'ar': {
        'welcome': 'مرحباً! اختر لغتك:',
        'selected': 'تم اختيار اللغة',
        'main': '📎 أرسل رابط للتحميل أو اكتب للبحث:',
        'download': '⏳ جاري التحميل...',
        'done': '✅ تم التحميل بنجاح!',
        'error': '❌ حدث خطأ. تحقق من الرابط وحاول لاحقاً',
        'no_results': '❌ لا توجد نتائج',
        'searching': '⏳ جاري البحث...',
        'select': '🎬 اختر صيغة التحميل:',
        'send_link': '📎 أرسل الرابط:',
        'send_search': '📎 اكتب اسم الفيديو للبحث:',
        'help_title': '📌 طريقة الاستخدام:',
        'help_text': '1️⃣ أرسل رابط للتحميل مباشرة\n2️⃣ اكتب اسم للبحث في يوتيوب\n3️⃣ اختر جودة التحميل\n\n📧 للمشاكل: mohamedeslammaklad700@gmail.com',
        'link': '🔗 رابط',
        'search': '🔍 بحث'
    },
    'en': {
        'welcome': 'Hello! Choose language:',
        'selected': 'Language selected',
        'main': '📎 Send link to download or type to search:',
        'download': '⏳ Downloading...',
        'done': '✅ Downloaded successfully!',
        'error': '❌ Error. Check link and try again',
        'no_results': '❌ No results found',
        'searching': '⏳ Searching...',
        'select': '🎬 Select download format:',
        'send_link': '📎 Send link:',
        'send_search': '📎 Enter video name:',
        'help_title': '📌 How to use:',
        'help_text': '1️⃣ Send link to download\n2️⃣ Type name to search YouTube\n3️⃣ Select quality\n\n📧 For problems: mohamedeslammaklad700@gmail.com',
        'link': '🔗 Link',
        'search': '🔍 Search'
    }
}

# ==================== KEYBOARDS ====================
def kb_lang():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🇸🇦 العربية', callback_data='lang_ar')],
        [InlineKeyboardButton('🇬🇧 English', callback_data='lang_en')]
    ])

def kb_main(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(MSG[lang]['link'], callback_data='btn_link')],
        [InlineKeyboardButton(MSG[lang]['search'], callback_data='btn_search')]
    ])

def kb_dl():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📥 Video', callback_data='dl_video')],
        [InlineKeyboardButton('🎵 MP3', callback_data='dl_mp3')],
        [InlineKeyboardButton('⬅️ Back', callback_data='dl_back')]
    ])

# ==================== DOWNLOAD ====================
def download_file(url, mp3=False):
    folder = '/tmp'
    os.makedirs(folder, exist_ok=True)
    
    try:
        if mp3:
            cmd = ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', f'{folder}/out.%(ext)s', url]
        else:
            cmd = ['yt-dlp', '-f', 'best', '-o', f'{folder}/out.%(ext)s', url]
        
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
        cmd = ['yt-dlp', f'ytsearch10:{query}', '--skip-download', '-J']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return []
        
        import json
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
        
    except Exception as e:
        logger.error(f'Search error: {e}')
        return []

# ==================== COMMANDS ====================

# /start
async def start(update, context):
    u = get_user(update.effective_user.id)
    if u['lang'] is None:
        await update.message.reply_text(MSG['ar']['welcome'], reply_markup=kb_lang())
    else:
        await update.message.reply_text(MSG[u['lang']]['main'], reply_markup=kb_main(u['lang']))

# /help
async def help_cmd(update, context):
    u = get_user(update.effective_user.id)
    l = u.get('lang', 'en')
    await update.message.reply_text(MSG[l]['help_title'] + '\n\n' + MSG[l]['help_text'])

# /language
async def language_cmd(update, context):
    await update.message.reply_text(MSG['ar']['welcome'], reply_markup=kb_lang())

# ==================== CALLBACKS ====================

async def lang_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    u['lang'] = 'ar' if q.data == 'lang_ar' else 'en'
    await q.edit_message_text(MSG[u['lang']]['selected'])
    await q.message.reply_text(MSG[u['lang']]['main'], reply_markup=kb_main(u['lang']))

async def btn_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    l = u.get('lang', 'en')
    
    if q.data == 'btn_link':
        u['action'] = 'link'
        await q.edit_message_text(MSG[l]['send_link'])
    elif q.data == 'btn_search':
        u['action'] = 'search'
        await q.edit_message_text(MSG[l]['send_search'])

# ==================== MESSAGE HANDLER ====================
async def msg_h(update, context):
    u = get_user(update.effective_user.id)
    l = u.get('lang', 'en')
    txt = update.message.text
    
    is_link = 'http' in txt.lower() or 'www' in txt.lower()
    
    # If link sent (auto-download)
    if is_link:
        await update.message.reply_text(MSG[l]['download'])
        
        f = download_file(txt, mp3=False)
        
        if f and os.path.exists(f):
            try:
                await update.message.reply_video(open(f, 'rb'))
                os.remove(f)
                await update.message.reply_text(MSG[l]['done'])
            except Exception as e:
                logger.error(f'Send error: {e}')
                await update.message.reply_text(MSG[l]['error'])
        else:
            await update.message.reply_text(MSG[l]['error'])
    
    # If text (search)
    else:
        await update.message.reply_text(MSG[l]['searching'])
        
        r = search_videos(txt)
        
        if not r:
            await update.message.reply_text(MSG[l]['no_results'])
            return
        
        txt_msg = f'📋 Results for "{txt}":\n\n'
        btns = []
        
        for i, v in enumerate(r, 1):
            txt_msg += f"{i}. {v['title']}\n   {v['channel']}\n\n"
            btns.append([InlineKeyboardButton(str(i), callback_data=f"v_{v['video_id']}")])
        
        await update.message.reply_text(txt_msg, reply_markup=InlineKeyboardMarkup(btns))

async def vid_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    l = u.get('lang', 'en')
    
    vid = q.data.replace('v_', '')
    u['url'] = f'https://youtube.com/watch?v={vid}'
    
    await q.edit_message_text(MSG[l]['select'], reply_markup=kb_dl())

async def dl_cb(update, context):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    l = u.get('lang', 'en')
    
    # Back button
    if q.data == 'dl_back':
        u['url'] = None
        await q.edit_message_text(MSG[l]['main'], reply_markup=kb_main(l))
        return
    
    mp3 = (q.data == 'dl_mp3')
    url = u.get('url')
    
    if not url:
        await q.message.reply_text(MSG[l]['error'])
        return
    
    await q.edit_message_text(MSG[l]['download'])
    
    f = download_file(url, mp3=mp3)
    
    if f and os.path.exists(f):
        try:
            if mp3:
                await q.message.reply_audio(open(f, 'rb'))
            else:
                await q.message.reply_video(open(f, 'rb'))
            os.remove(f)
            await q.message.reply_text(MSG[l]['done'])
        except Exception as e:
            logger.error(f'Send error: {e}')
            await q.message.reply_text(MSG[l]['error'])
    else:
        await q.message.reply_text(MSG[l]['error'])

async def err(update, context):
    logger.error(f'Error: {context.error}')

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('language', language_cmd))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(lang_cb, pattern='^lang_'))
    app.add_handler(CallbackQueryHandler(btn_cb, pattern='^btn_'))
    app.add_handler(CallbackQueryHandler(vid_cb, pattern='^v_'))
    app.add_handler(CallbackQueryHandler(dl_cb, pattern='^dl_'))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    app.add_error_handler(err)
    
    print('Bot running')
    app.run_polling()

if __name__ == '__main__':
    main()
