"""
🔊 SpeakEasyFastBot - Fast Language Translator with Text-to-Speech
Translate text between multiple languages with instant audio pronunciation
"""

import os
import io
import re
import logging
import base64
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# For text-to-speech
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ gTTS not installed. Audio features disabled.")

# For translation
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("⚠️ deep-translator not installed. Translation features disabled.")

# ==================== LOGGING ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Try multiple possible token variable names
BOT_TOKEN = (
    os.environ.get("TELEGRAM_TOKEN") or
    os.environ.get("TELEGRAM_BOT_TOKEN") or
    os.environ.get("BOT_TOKEN")
)

# If token is not set, try reading from .env file
if not BOT_TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = (
            os.environ.get("TELEGRAM_TOKEN") or
            os.environ.get("TELEGRAM_BOT_TOKEN") or
            os.environ.get("BOT_TOKEN")
        )
    except:
        pass

# If still no token, show error
if not BOT_TOKEN:
    logger.error("=" * 60)
    logger.error("❌ ERROR: No Telegram Bot Token found!")
    logger.error("=" * 60)
    raise ValueError("❌ No Telegram Bot Token found in environment variables!")

BOT_NAME = "SpeakEasyFastBot"
BOT_USERNAME = "speakeasyfastbot"
BOT_VERSION = "1.0.0"

# ==================== LANGUAGE DATA ====================

# Language codes with names, flags, and TTS support
LANG_CODES = {
    "en": {"name": "English", "flag": "🇬🇧", "tts": True},
    "es": {"name": "Spanish", "flag": "🇪🇸", "tts": True},
    "fr": {"name": "French", "flag": "🇫🇷", "tts": True},
    "de": {"name": "German", "flag": "🇩🇪", "tts": True},
    "it": {"name": "Italian", "flag": "🇮🇹", "tts": True},
    "pt": {"name": "Portuguese", "flag": "🇵🇹", "tts": True},
    "ru": {"name": "Russian", "flag": "🇷🇺", "tts": True},
    "zh-cn": {"name": "Chinese (Simplified)", "flag": "🇨🇳", "tts": True},
    "ja": {"name": "Japanese", "flag": "🇯🇵", "tts": True},
    "ko": {"name": "Korean", "flag": "🇰🇷", "tts": True},
    "ar": {"name": "Arabic", "flag": "🇸🇦", "tts": True},
    "hi": {"name": "Hindi", "flag": "🇮🇳", "tts": True},
    "tr": {"name": "Turkish", "flag": "🇹🇷", "tts": True},
    "nl": {"name": "Dutch", "flag": "🇳🇱", "tts": True},
    "pl": {"name": "Polish", "flag": "🇵🇱", "tts": True},
    "uk": {"name": "Ukrainian", "flag": "🇺🇦", "tts": True},
    "vi": {"name": "Vietnamese", "flag": "🇻🇳", "tts": True},
    "th": {"name": "Thai", "flag": "🇹🇭", "tts": True},
    "id": {"name": "Indonesian", "flag": "🇮🇩", "tts": True},
    "ms": {"name": "Malay", "flag": "🇲🇾", "tts": True},
    "fa": {"name": "Persian", "flag": "🇮🇷", "tts": True},
    "he": {"name": "Hebrew", "flag": "🇮🇱", "tts": True},
    "sv": {"name": "Swedish", "flag": "🇸🇪", "tts": True},
    "no": {"name": "Norwegian", "flag": "🇳🇴", "tts": True},
    "da": {"name": "Danish", "flag": "🇩🇰", "tts": True},
    "fi": {"name": "Finnish", "flag": "🇫🇮", "tts": True},
    "el": {"name": "Greek", "flag": "🇬🇷", "tts": True},
}

# TTS supported languages (gTTS subset)
TTS_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh-cn": "Chinese (Mandarin)",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "el": "Greek",
}

# ==================== USER DATA ====================

user_data: Dict[int, Dict] = {}

def get_user_data(user_id: int) -> Dict:
    """Get or create user data"""
    if user_id not in user_data:
        user_data[user_id] = {
            "source_lang": None,  # None = auto-detect
            "target_lang": "es",
            "total_translations": 0,
            "total_audio": 0,
            "favorite_langs": defaultdict(int),
            "last_text": "",
            "last_translation": "",
            "auto_audio": True,  # Auto-play audio after translation
            "tts_speed": "normal",  # normal, slow
        }
    return user_data[user_id]

# ==================== KEYBOARDS ====================

def get_main_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🌐 Translate & Speak", callback_data="translate")],
        [InlineKeyboardButton("🔊 Text to Speech Fast", callback_data="tts")],
        [InlineKeyboardButton("🔄 Swap Languages", callback_data="swap")],
        [InlineKeyboardButton("📋 Languages", callback_data="languages")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard(page: int = 0, selected: str = None, mode: str = "target"):
    """Create language selection keyboard"""
    keyboard = []
    lang_items = list(LANG_CODES.items())
    per_page = 8
    start = page * per_page
    end = min(start + per_page, len(lang_items))
    
    for i in range(start, end, 2):
        row = []
        for j in range(2):
            if i + j < end:
                code, lang = lang_items[i + j]
                is_selected = (code == selected)
                has_tts = "🔊" if LANG_CODES[code].get("tts", False) else ""
                text = f"{'✅ ' if is_selected else ''}{lang['flag']} {lang['name']} {has_tts}"
                row.append(InlineKeyboardButton(
                    text,
                    callback_data=f"lang_{mode}_{code}"
                ))
        keyboard.append(row)
    
    # Navigation buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"langpage_{mode}_{page-1}"))
    if end < len(lang_items):
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"langpage_{mode}_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(user_id: int):
    """Create settings keyboard"""
    data = get_user_data(user_id)
    source = data.get("source_lang", "auto")
    target = data.get("target_lang", "es")
    auto_audio = data.get("auto_audio", True)
    tts_speed = data.get("tts_speed", "normal")
    
    source_name = LANG_CODES.get(source, {}).get("name", "Auto Detect") if source else "Auto Detect"
    target_name = LANG_CODES.get(target, {}).get("name", "Spanish")
    
    keyboard = [
        [InlineKeyboardButton(
            f"🔍 Source: {'Auto' if not source else source_name}",
            callback_data="set_source"
        )],
        [InlineKeyboardButton(
            f"🎯 Target: {target_name}",
            callback_data="set_target"
        )],
        [InlineKeyboardButton(
            f"{'✅' if auto_audio else '❌'} Auto Audio",
            callback_data="toggle_audio"
        )],
        [InlineKeyboardButton(
            f"⏱️ Speed: {tts_speed.capitalize()}",
            callback_data="toggle_speed"
        )],
        [InlineKeyboardButton(
            "🔄 Swap Languages",
            callback_data="swap"
        )],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== TRANSLATION FUNCTIONS ====================

def translate_text(text: str, dest_lang: str, src_lang: str = None) -> Dict:
    """
    Translate text using deep-translator
    Returns: Dict with translation details
    """
    if not TRANSLATION_AVAILABLE:
        return {
            "error": "Translation service unavailable. Please try again later."
        }
    
    try:
        # Create translator instance
        translator = GoogleTranslator(source='auto', target=dest_lang)
        
        # If source language is specified, use it
        if src_lang and src_lang in LANG_CODES:
            translator = GoogleTranslator(source=src_lang, target=dest_lang)
        
        # Perform translation
        translated_text = translator.translate(text)
        
        # Get language names
        src_name = LANG_CODES.get(src_lang, {}).get("name", "Auto-detected") if src_lang else "Auto-detected"
        dest_name = LANG_CODES.get(dest_lang, {}).get("name", dest_lang)
        
        return {
            "original": text,
            "translated": translated_text,
            "source_lang": src_lang or 'auto',
            "target_lang": dest_lang,
            "source_name": src_name,
            "target_name": dest_name,
            "auto_detected": not bool(src_lang)
        }
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return {
            "error": f"Translation failed: {str(e)}"
        }

# ==================== TEXT-TO-SPEECH FUNCTIONS ====================

def text_to_speech(text: str, lang: str = "en", slow: bool = False) -> Optional[bytes]:
    """
    Convert text to speech using gTTS
    Returns: Audio bytes or None
    """
    if not TTS_AVAILABLE:
        return None
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
        
        # Generate speech
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(temp_path)
        
        # Read the audio file
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up
        os.unlink(temp_path)
        
        return audio_data
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = str(user.id)
    data = get_user_data(user_id)
    
    welcome = (
        f"🔊 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or user.first_name}!\n\n"
        f"Your **fast** language translation assistant with **Text-to-Speech**!\n\n"
        f"⚡ **Features:**\n"
        f"• 🌐 Translate between 30+ languages\n"
        f"• 🔊 Instant audio pronunciation\n"
        f"• 🔍 Auto-detect source language\n"
        f"• 🔄 Quick language swap\n"
        f"• ⏱️ Adjustable speech speed\n"
        f"• 📊 Usage statistics\n\n"
        f"📊 **Your Stats:**\n"
        f"• Total translations: {data['total_translations']}\n"
        f"• Total audio: {data['total_audio']}\n\n"
        f"⬇️ Send me any text or use the buttons below!"
    )
    
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        f"📖 **{BOT_NAME} User Guide**\n\n"
        "**🌐 Translate & Speak:**\n"
        "• Send any text message\n"
        "• I'll auto-detect the language\n"
        "• Get translation + audio instantly\n\n"
        "**🔊 Text to Speech Fast:**\n"
        "• Click 'Text to Speech Fast'\n"
        "• Send any text\n"
        "• Get audio pronunciation\n\n"
        "**⚙️ Settings:**\n"
        "• Change target language\n"
        "• Toggle auto-audio\n"
        "• Adjust speech speed (Normal/Slow)\n"
        "• Swap languages\n\n"
        "**📌 Commands:**\n"
        "/start - Main menu\n"
        "/help - This help\n"
        "/stats - Your statistics\n"
        "/languages - List all languages"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    
    fav_langs = data.get("favorite_langs", defaultdict(int))
    top_langs = sorted(fav_langs.items(), key=lambda x: x[1], reverse=True)[:5]
    
    stats_text = (
        f"📊 **Your Statistics**\n\n"
        f"🌐 Total translations: {data['total_translations']}\n"
        f"🔊 Total audio: {data['total_audio']}\n"
        f"🔤 Source: {'Auto' if not data.get('source_lang') else LANG_CODES.get(data['source_lang'], {}).get('name', 'Auto')}\n"
        f"🎯 Target: {LANG_CODES.get(data['target_lang'], {}).get('name', 'Spanish')}\n"
        f"⏱️ Speed: {data.get('tts_speed', 'normal').capitalize()}\n"
        f"📅 Account active since: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    )
    
    if top_langs:
        stats_text += "🏆 **Top Languages:**\n"
        for lang_code, count in top_langs:
            lang_name = LANG_CODES.get(lang_code, {}).get("name", lang_code)
            flag = LANG_CODES.get(lang_code, {}).get("flag", "🌐")
            stats_text += f"• {flag} {lang_name}: {count}\n"
    
    await update.message.reply_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /languages command"""
    lang_list = "🌐 **Supported Languages**\n\n"
    lang_list += "🔊 = Text-to-Speech supported\n\n"
    for code, lang in sorted(LANG_CODES.items(), key=lambda x: x[1]['name']):
        tts_mark = " 🔊" if lang.get("tts", False) else ""
        lang_list += f"{lang['flag']} **{lang['name']}** `{code}`{tts_mark}\n"
    
    await update.message.reply_text(
        lang_list,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    action = query.data
    
    # ===== MAIN ACTIONS =====
    
    if action == "translate":
        await query.edit_message_text(
            "🌐 **Send me text to translate!**\n\n"
            "I'll auto-detect the language and translate it.\n"
            "I'll also send audio pronunciation instantly.\n\n"
            "⚙️ Use Settings to change target language.\n\n"
            "Just send any text message!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = "translate_waiting"
        
    elif action == "tts":
        await query.edit_message_text(
            "🔊 **Text to Speech Fast**\n\n"
            "Send me any text, and I'll convert it to speech instantly!\n\n"
            "You can choose the language below:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Select Language", callback_data="tts_lang")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        context.user_data["action"] = "tts_waiting"
        
    elif action == "tts_lang":
        await query.edit_message_text(
            "📋 **Select TTS Language**\n\n"
            "Choose the language for audio:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard(0, data.get("tts_lang", "en"), "tts")
        )
        
    elif action == "swap":
        # Swap source and target
        source = data.get("source_lang")
        target = data.get("target_lang", "es")
        data["source_lang"] = target
        data["target_lang"] = source if source else "en"
        
        source_name = LANG_CODES.get(data["source_lang"], {}).get("name", "Auto Detect") if data["source_lang"] else "Auto Detect"
        target_name = LANG_CODES.get(data["target_lang"], {}).get("name", "English")
        
        await query.edit_message_text(
            f"🔄 **Languages Swapped!**\n\n"
            f"Source: {source_name}\n"
            f"Target: {target_name}\n\n"
            f"Send me text to translate!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = "translate_waiting"
        
    elif action == "languages":
        await query.edit_message_text(
            "📋 **Select Target Language**\n\n"
            "Choose your target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard(0, data.get("target_lang", "es"), "target")
        )
        
    elif action == "settings":
        await query.edit_message_text(
            "⚙️ **Settings**\n\n"
            "Customize your translation experience:",
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(user_id)
        )
        
    elif action == "stats":
        fav_langs = data.get("favorite_langs", defaultdict(int))
        top_langs = sorted(fav_langs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        stats_text = (
            f"📊 **Your Statistics**\n\n"
            f"🌐 Total translations: {data['total_translations']}\n"
            f"🔊 Total audio: {data['total_audio']}\n"
            f"🔤 Source: {'Auto' if not data.get('source_lang') else LANG_CODES.get(data['source_lang'], {}).get('name', 'Auto')}\n"
            f"🎯 Target: {LANG_CODES.get(data['target_lang'], {}).get('name', 'Spanish')}\n"
            f"⏱️ Speed: {data.get('tts_speed', 'normal').capitalize()}\n"
            f"📅 Account active since: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        )
        
        if top_langs:
            stats_text += "🏆 **Top Languages:**\n"
            for lang_code, count in top_langs:
                lang_name = LANG_CODES.get(lang_code, {}).get("name", lang_code)
                flag = LANG_CODES.get(lang_code, {}).get("flag", "🌐")
                stats_text += f"• {flag} {lang_name}: {count}\n"
        
        await query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "help":
        help_text = (
            f"📖 **{BOT_NAME} User Guide**\n\n"
            "**🌐 Translate & Speak:**\n"
            "• Send any text message\n"
            "• I'll auto-detect the language\n"
            "• Get translation + audio instantly\n\n"
            "**🔊 Text to Speech Fast:**\n"
            "• Click 'Text to Speech Fast'\n"
            "• Send any text\n"
            "• Get audio pronunciation\n\n"
            "**⚙️ Settings:**\n"
            "• Change target language\n"
            "• Toggle auto-audio\n"
            "• Adjust speech speed\n"
            "• Swap languages\n\n"
            "**📌 Commands:**\n"
            "/start - Main menu\n"
            "/help - This help\n"
            "/stats - Your statistics"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None
        
    # ===== SETTINGS =====
    
    elif action == "set_source":
        await query.edit_message_text(
            "📋 **Select Source Language**\n\n"
            "Choose the source language (or select 'Auto' for auto-detection):",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard(0, data.get("source_lang", None), "source")
        )
        
    elif action == "set_target":
        await query.edit_message_text(
            "📋 **Select Target Language**\n\n"
            "Choose the target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard(0, data.get("target_lang", "es"), "target")
        )
        
    elif action == "toggle_audio":
        data["auto_audio"] = not data.get("auto_audio", True)
        await query.edit_message_text(
            "⚙️ **Settings**\n\n"
            f"Auto Audio: {'✅ On' if data.get('auto_audio', True) else '❌ Off'}\n\n"
            "Customize your translation experience:",
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(user_id)
        )
        
    elif action == "toggle_speed":
        current = data.get("tts_speed", "normal")
        data["tts_speed"] = "slow" if current == "normal" else "normal"
        await query.edit_message_text(
            "⚙️ **Settings**\n\n"
            f"Speech Speed: {data['tts_speed'].capitalize()}\n\n"
            "Customize your translation experience:",
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(user_id)
        )
        
    # ===== LANGUAGE SELECTION =====
    
    elif action.startswith("lang_source_"):
        lang_code = action.replace("lang_source_", "")
        if lang_code in LANG_CODES:
            data["source_lang"] = lang_code
            lang_name = LANG_CODES[lang_code]["name"]
            await query.edit_message_text(
                f"✅ **Source Language Set!**\n\n"
                f"Source: {LANG_CODES[lang_code]['flag']} {lang_name}\n\n"
                f"Send me text to translate!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            context.user_data["action"] = "translate_waiting"
            
    elif action.startswith("lang_target_"):
        lang_code = action.replace("lang_target_", "")
        if lang_code in LANG_CODES:
            data["target_lang"] = lang_code
            lang_name = LANG_CODES[lang_code]["name"]
            await query.edit_message_text(
                f"✅ **Target Language Set!**\n\n"
                f"Target: {LANG_CODES[lang_code]['flag']} {lang_name}\n\n"
                f"Send me text to translate!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            context.user_data["action"] = "translate_waiting"
            
    elif action.startswith("lang_tts_"):
        lang_code = action.replace("lang_tts_", "")
        if lang_code in LANG_CODES:
            data["tts_lang"] = lang_code
            lang_name = LANG_CODES[lang_code]["name"]
            await query.edit_message_text(
                f"✅ **TTS Language Set!**\n\n"
                f"Audio Language: {LANG_CODES[lang_code]['flag']} {lang_name}\n\n"
                f"Send me text to convert to speech!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            context.user_data["action"] = "tts_waiting"
            
    # ===== PLAY AUDIO =====
    
    elif action.startswith("play_audio_"):
        lang_code = action.replace("play_audio_", "")
        if "last_translation" in context.user_data:
            text = context.user_data["last_translation"]
            speed = data.get("tts_speed", "normal") == "slow"
            audio_data = text_to_speech(text, lang_code, speed)
            
            if audio_data:
                await query.message.reply_voice(
                    voice=io.BytesIO(audio_data),
                    caption=f"🔊 Playing: {text[:50]}..."
                )
                data["total_audio"] += 1
            else:
                await query.message.reply_text(
                    "❌ Failed to generate audio. Please try again.",
                    reply_markup=get_main_keyboard()
                )
        else:
            await query.message.reply_text(
                "❌ No translation found. Please translate some text first!",
                reply_markup=get_main_keyboard()
            )
    
    # ===== LANGUAGE PAGE NAVIGATION =====
    
    elif action.startswith("langpage_"):
        parts = action.split("_")
        if len(parts) == 3:
            mode = parts[1]
            page = int(parts[2])
            await query.edit_message_text(
                "📋 **Select Language**\n\n"
                f"Choose your language:",
                parse_mode="Markdown",
                reply_markup=get_language_keyboard(page, data.get("target_lang", "es"), mode)
            )

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for translation and TTS"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    text = update.message.text.strip()
    action = context.user_data.get("action", "")
    
    if not text:
        await update.message.reply_text(
            "❌ Please send some text!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # ===== TTS MODE =====
    
    if action == "tts_waiting":
        # Get TTS language
        tts_lang = data.get("tts_lang", "en")
        speed = data.get("tts_speed", "normal") == "slow"
        
        processing_msg = await update.message.reply_text(
            f"🔊 **Generating speech...**\n\n"
            f"Text: {text[:50]}{'...' if len(text) > 50 else ''}\n"
            f"Language: {LANG_CODES.get(tts_lang, {}).get('name', 'English')}\n"
            f"Speed: {data.get('tts_speed', 'normal').capitalize()}\n\n"
            f"⏳ Please wait...",
            parse_mode="Markdown"
        )
        
        audio_data = text_to_speech(text, tts_lang, speed)
        
        await processing_msg.delete()
        
        if audio_data:
            await update.message.reply_voice(
                voice=io.BytesIO(audio_data),
                caption=f"🔊 **Text to Speech**\n\n"
                       f"📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}\n"
                       f"🌐 Language: {LANG_CODES.get(tts_lang, {}).get('name', 'English')}\n"
                       f"⏱️ Speed: {data.get('tts_speed', 'normal').capitalize()}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Retry", callback_data=f"play_audio_{tts_lang}")],
                    [InlineKeyboardButton("🎤 Change Language", callback_data="tts_lang")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
                ])
            )
            data["total_audio"] += 1
        else:
            await update.message.reply_text(
                "❌ **TTS Failed**\n\n"
                "Could not generate audio. Please try again or use a different language.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        
        context.user_data["action"] = None
        return
    
    # ===== TRANSLATE MODE =====
    
    if action == "translate_waiting" or True:
        # Get settings
        src_lang = data.get("source_lang")  # None = auto-detect
        dest_lang = data.get("target_lang", "es")
        auto_audio = data.get("auto_audio", True)
        speed = data.get("tts_speed", "normal") == "slow"
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🌐 **Translating...**\n\n"
            "Please wait...",
            parse_mode="Markdown"
        )
        
        # Translate
        result = translate_text(text, dest_lang, src_lang)
        
        await processing_msg.delete()
        
        if "error" in result:
            await update.message.reply_text(
                f"❌ **Translation Failed**\n\n{result['error']}",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Update stats
        data["total_translations"] += 1
        data["favorite_langs"][result["target_lang"]] += 1
        data["last_text"] = text
        data["last_translation"] = result["translated"]
        context.user_data["last_translation"] = result["translated"]
        
        # Format response
        source_name = LANG_CODES.get(result["source_lang"], {}).get("name", "Auto-detected") if result["source_lang"] != 'auto' else 'Auto-detected'
        target_name = LANG_CODES.get(result["target_lang"], {}).get("name", result["target_lang"])
        
        response = (
            f"🌐 **Translation**\n\n"
            f"🔤 **From:** {source_name}\n"
            f"🔤 **To:** {target_name}\n"
            f"{'🔍 Auto-detected' if result.get('auto_detected', True) else ''}\n\n"
            f"📝 **Original:**\n{result['original']}\n\n"
            f"🔄 **Translated:**\n{result['translated']}\n\n"
        )
        
        # Generate audio if enabled
        audio_data = None
        if auto_audio and TTS_AVAILABLE:
            tts_lang = result["target_lang"]
            if tts_lang in TTS_LANGUAGES:
                audio_data = text_to_speech(result["translated"], tts_lang, speed)
        
        # Send response with or without audio
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔊 Play Audio", callback_data=f"play_audio_{result['target_lang']}")],
            [InlineKeyboardButton("🔄 Swap Languages", callback_data="swap")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
        ])
        
        if audio_data:
            await update.message.reply_voice(
                voice=io.BytesIO(audio_data),
                caption=response,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            data["total_audio"] += 1
        else:
            await update.message.reply_text(
                response,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        
        context.user_data["action"] = "translate_waiting"

# ==================== MAIN ====================

async def post_init(application):
    """Post initialization"""
    logger.info("=" * 60)
    logger.info(f"🔊 {BOT_NAME} Started Successfully!")
    logger.info(f"🤖 Username: @{BOT_USERNAME}")
    logger.info(f"📦 Version: {BOT_VERSION}")
    logger.info(f"🌍 Supported Languages: {len(LANG_CODES)}")
    logger.info(f"✅ Real Translation: {'Enabled' if TRANSLATION_AVAILABLE else 'Disabled'}")
    logger.info(f"✅ Text-to-Speech: {'Enabled' if TTS_AVAILABLE else 'Disabled'}")
    logger.info("=" * 60)
    logger.info("✅ Bot is ready to translate and speak!")
    logger.info("=" * 60)

def main():
    """Main entry point"""
    logger.info(f"🚀 Starting {BOT_NAME}...")
    logger.info(f"📡 Using token: {BOT_TOKEN[:15]}...{BOT_TOKEN[-5:]}")
    
    if not TRANSLATION_AVAILABLE:
        logger.warning("⚠️ deep-translator not installed! Install with: pip install deep-translator")
    
    if not TTS_AVAILABLE:
        logger.warning("⚠️ gTTS not installed! Install with: pip install gTTS")
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("languages", languages_command))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Bot is polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
