# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 3.5 [Hinglish Enabled]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import random
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from deep_translator import GoogleTranslator 
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# Database Connections
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
chatdb = MongoClient(MONGO_URL)
worddb = MongoClient(WORD_MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
chatai = worddb["Word"]["WordDb"]
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# Languages list (Hinglish Added)
languages = {
    'Hinglish': 'hi-en', # New Hinglish Option
    'English': 'en', 'Hindi': 'hi', 'Bhojpuri': 'bho', 'Urdu': 'ur',
    'Marathi': 'mr', 'Gujarati': 'gu', 'Tamil': 'ta', 'Telugu': 'te',
    'Punjabi': 'pa', 'Bengali': 'bn', 'Malayalam': 'ml', 'Kannada': 'kn',
    'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Russian': 'ru'
}

CHATBOT_ON = [
    [
        InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="enable_chatbot"),
        InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="disable_chatbot"),
    ],
]

def generate_language_buttons(languages):
    buttons = []
    current_row = []
    for lang, code in languages.items():
        current_row.append(InlineKeyboardButton(lang, callback_data=f'setlang_{code}'))
        if len(current_row) == 3:  
            buttons.append(current_row)
            current_row = []  
    if current_row: buttons.append(current_row)
    return InlineKeyboardMarkup(buttons)

def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else "hi-en"

# --- COMMANDS ---

@nexichat.on_message(filters.command(["chatbotlang", "setchatbotlang"]))
async def set_language(client, message):
    await message.reply_text(
        "✨ **ᴘʟᴇᴀsᴇ sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴄʜᴀᴛ ʟᴀɴɢᴜᴀɢᴇ:**\n\n*Hinglish means bot will use mixed Hindi-English.*", 
        reply_markup=generate_language_buttons(languages)
    )

@nexichat.on_message(filters.command("chatbot"))
async def chaton(client, message):
    await message.reply_text(
        f"🤖 **ᴄʜᴀᴛʙᴏᴛ sᴇᴛᴛɪɴɢs**\n\nᴄʜᴀᴛ: {message.chat.title or 'Private'}\n**ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ:**",
        reply_markup=InlineKeyboardMarkup(CHATBOT_ON),
    )

@nexichat.on_message(filters.command(["resetlang", "nolang"]))
async def reset_lang(client, message):
    lang_db.update_one({"chat_id": message.chat.id}, {"$set": {"language": "hi-en"}}, upsert=True)
    await message.reply_text("✅ **Bot language reset to Hinglish (Mixed).**")

# --- CHATBOT CORE LOGIC ---

@nexichat.on_message((filters.text | filters.sticker | filters.photo | filters.video | filters.audio) & ~filters.bot)
async def chatbot_response(client: Client, message: Message):
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    if message.text and any(message.text.startswith(prefix) for prefix in ["!", "/", ".", "?", "@", "#"]):
        return

    # Trigger logic: Private Chat OR Reply to Bot in Groups
    is_private = message.chat.type == ChatType.PRIVATE
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == nexichat.id

    if is_private or is_reply_to_bot:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        query_text = message.text if message.text else "sticker_or_media"
        reply_data = await get_reply(query_text)
        
        if reply_data:
            response_text = reply_data["text"]
            chat_lang = get_chat_language(message.chat.id)

            # --- HINGLISH/MIXED LOGIC ---
            # If lang is 'hi-en' or 'en', we don't translate (keeps it natural)
            if chat_lang not in ["hi-en", "en", "nolang"] and reply_data["check"] == "none":
                try:
                    response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
                except:
                    pass # Fallback to original if translation fails

            if reply_data["check"] == "sticker":
                await message.reply_sticker(reply_data["text"])
            elif reply_data["check"] == "photo":
                await message.reply_photo(reply_data["text"])
            elif reply_data["check"] == "video":
                await message.reply_video(reply_data["text"])
            elif reply_data["check"] == "audio":
                await message.reply_audio(reply_data["text"])
            else:
                await message.reply_text(response_text)
        else:
            if is_private:
                await message.reply_text("🤔?")

    # Learning Logic: Save replies
    if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
        await save_reply(message.reply_to_message, message)

async def get_reply(word: str):
    is_chat = list(chatai.find({"word": word}))
    if not is_chat:
        return None
    return random.choice(is_chat)

async def save_reply(original_message: Message, reply_message: Message):
    try:
        if not original_message.text: return
        word = original_message.text
        content, check = "", "none"

        if reply_message.sticker:
            content, check = reply_message.sticker.file_id, "sticker"
        elif reply_message.photo:
            content, check = reply_message.photo.file_id, "photo"
        elif reply_message.video:
            content, check = reply_message.video.file_id, "video"
        elif reply_message.text:
            content, check = reply_message.text, "none"

        if content:
            if not chatai.find_one({"word": word, "text": content}):
                chatai.insert_one({"word": word, "text": content, "check": check})
    except:
        pass

# --- CALLBACK HANDLERS ---
@nexichat.on_callback_query(filters.regex(r"setlang_|enable_chatbot|disable_chatbot|choose_lang"))
async def cb_handler(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    
    if query.data.startswith("setlang_"):
        lang_code = query.data.split("_")[1]
        lang_db.update_one({"chat_id": chat_id}, {"$set": {"language": lang_code}}, upsert=True)
        await query.answer(f"Language set to {lang_code}!", show_alert=True)
        await query.edit_message_text(f"✅ **Chat language updated to: {lang_code.upper()}**")

    elif query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("Chatbot Enabled!")
        await query.edit_message_text("✅ **Chatbot is now ACTIVE in this chat.**")

    elif query.data == "disable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("Chatbot Disabled!")
        await query.edit_message_text("❌ **Chatbot is now INACTIVE in this chat.**")

# ======================================================
# 🚀 NEXT-GEN AI MODULE LOADED
# ======================================================
