# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 5.0 [Female Persona & Anti-Abuse]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import random
import re
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

# --- ABUSE FILTER & PERSONA SETTINGS ---
# Yahan wo words likhein jo bot na bole aur na hi seekhe
BANNED_WORDS = ["gaali1", "gaali2", "behenchod", "madarchod", "ganda_word", "chutiya", "saale"] 

def make_female_and_polite(text):
    """Bot ki language ko female aur izzatdar banane ke liye"""
    # Male words ko Female mein badalna
    replacements = {
        "karta hoon": "karti hoon",
        "karta hu": "karti hu",
        "raha hoon": "rahi hoon",
        "raha hu": "rahi hu",
        "gaya tha": "gayi thi",
        "aaunga": "aaungi",
        "karunga": "karungi",
        "khata hoon": "khati hoon",
        "piya hai": "piya hai", # Neutral
        "bhai": "ji",
        "abe": "ji",
        "tu ": "aap ",
        "tera": "aapka",
        "tujhe": "aapko"
    }
    for male, female in replacements.items():
        text = re.sub(f"\\b{male}\\b", female, text, flags=re.IGNORECASE)
    return text

def is_abusive(text):
    """Check if message has bad words"""
    for word in BANNED_WORDS:
        if word.lower() in text.lower():
            return True
    return False

# --- LANGUAGES ---
languages = {
    'Hinglish': 'hi-en',
    'English': 'en', 'Hindi': 'hi', 'Bhojpuri': 'bho', 'Urdu': 'ur',
    'Marathi': 'mr', 'Gujarati': 'gu', 'Tamil': 'ta', 'Telugu': 'te',
    'Punjabi': 'pa', 'Bengali': 'bn', 'Malayalam': 'ml', 'Kannada': 'kn'
}

CHATBOT_ON = [[InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="enable_chatbot"),
               InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="disable_chatbot")]]

# --- HELPER FUNCTIONS ---
def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else "hi-en"

# --- COMMANDS ---
@nexichat.on_message(filters.command(["chatbotlang", "setchatbotlang"]))
async def set_language(client, message):
    buttons = []
    current_row = []
    for lang, code in languages.items():
        current_row.append(InlineKeyboardButton(lang, callback_data=f'setlang_{code}'))
        if len(current_row) == 3: buttons.append(current_row); current_row = []
    if current_row: buttons.append(current_row)
    await message.reply_text("✨ **Select Language:**", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_message(filters.command("chatbot"))
async def chaton(client, message):
    await message.reply_text(f"🤖 **ChatBot Settings**\nChat: {message.chat.title or 'Private'}", reply_markup=InlineKeyboardMarkup(CHATBOT_ON))

# --- CHATBOT CORE LOGIC ---
@nexichat.on_message((filters.text | filters.sticker | filters.photo | filters.video | filters.audio) & ~filters.bot)
async def chatbot_response(client: Client, message: Message):
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    if message.text and any(message.text.startswith(prefix) for prefix in ["!", "/", ".", "?", "@", "#"]):
        return

    # Learning Logic: Save replies (Only if NOT ABUSIVE)
    if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
        if not is_abusive(message.text or ""):
            await save_reply(message.reply_to_message, message)

    await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    query_text = message.text.lower().strip() if message.text else "sticker_or_media"
    reply_data = await get_reply(query_text)
    
    if reply_data:
        response_text = reply_data["text"]
        
        # Check if stored response is abusive
        if is_abusive(response_text):
            return # Don't reply if the stored answer is bad

        # Female & Polite Filter
        if reply_data["check"] == "none":
            response_text = make_female_and_polite(response_text)

        chat_lang = get_chat_language(message.chat.id)
        if chat_lang not in ["hi-en", "en"] and reply_data["check"] == "none":
            try: response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
            except: pass 

        if reply_data["check"] == "sticker": await message.reply_sticker(reply_data["text"])
        elif reply_data["check"] == "photo": await message.reply_photo(reply_data["text"])
        elif reply_data["check"] == "video": await message.reply_video(reply_data["text"])
        elif reply_data["check"] == "audio": await message.reply_audio(reply_data["text"])
        else: await message.reply_text(response_text)
    else:
        if message.chat.type == ChatType.PRIVATE:
            await message.reply_text("Ji? Main samajh nahi paayi. ✨")

async def get_reply(word: str):
    is_chat = list(chatai.find({"word": word}))
    if not is_chat:
        is_chat = list(chatai.find({"word": {"$regex": word, "$options": "i"}}))
    return random.choice(is_chat) if is_chat else None

async def save_reply(original_message: Message, reply_message: Message):
    try:
        if not original_message.text: return
        word = original_message.text.lower().strip()
        content, check = "", "none"

        if reply_message.sticker: content, check = reply_message.sticker.file_id, "sticker"
        elif reply_message.photo: content, check = reply_message.photo.file_id, "photo"
        elif reply_message.text: content, check = reply_message.text, "none"

        if content and not is_abusive(content):
            if not chatai.find_one({"word": word, "text": content}):
                chatai.insert_one({"word": word, "text": content, "check": check})
    except: pass

@nexichat.on_callback_query(filters.regex(r"setlang_|enable_chatbot|disable_chatbot"))
async def cb_handler(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data.startswith("setlang_"):
        lang_code = query.data.split("_")[1]
        lang_db.update_one({"chat_id": chat_id}, {"$set": {"language": lang_code}}, upsert=True)
        await query.answer(f"Language set to {lang_code}")
        await query.edit_message_text(f"✅ Language updated to: {lang_code}")
    elif query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.edit_message_text("✅ **Chatbot Active! Main sabka reply karungi.**")
    elif query.data == "disable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.edit_message_text("❌ **Chatbot Inactive.**")
