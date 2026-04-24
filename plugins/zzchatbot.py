import random
import re
import aiohttp
from urllib.parse import quote
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from deep_translator import GoogleTranslator 
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# --- API Configuration ---
CHAT_API_URL = "https://api.safone.dev/chatbot?msg={}&user_id={}&char=Zoya"

# --- Female Tone Logic ---
def make_female_tone(text):
    if not text: return text
    replacements = {
        r"\braha hoon\b": "rahi hoon",
        r"\braha tha\b": "rahi thi",
        r"\braha hai\b": "rahi hai",
        r"\bgaya tha\b": "gayi thi",
        r"\bgaya\b": "gayi",
        r"\btha\b": "thi",
        r"\bkhata hoon\b": "khati hoon",
        r"\bkarunga\b": "karungi",
        r"\baaunga\b": "aaungi",
        r"\bdekhunga\b": "dekhungi",
        r"\bbhai\b": "behen 🌸",
        r"\bbhaiya\b": "didi",
        r"\bpagal\b": "pagli",
        r"\bhoon\b": "hoon ji ✨"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else "hi"

async def get_api_reply(user_id, word: str):
    try:
        msg = quote(word)
        url = CHAT_API_URL.format(msg, user_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response")
    except:
        return None

# --- Main Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else chat_id
    
    # 1. Database se check karein ki chatbot enabled hai ya nahi
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Commands ko ignore karein
    if message.text and message.text.startswith(("/", "!", ".")):
        return

    # 3. Message triggers
    user_text = message.text if message.text else ""
    me = await client.get_me()
    
    is_private = message.chat.type.value == "private"
    is_reply_to_me = False
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == me.id:
            is_reply_to_me = True
            
    # Agar bot ka naam mention kiya jaye
    is_mentioned = False
    if message.text and (f"@{me.username}" in message.text or me.first_name.lower() in message.text.lower()):
        is_mentioned = True

    # Group mein reply dene ke conditions:
    # 1. Private Chat ho
    # 2. Bot ko reply kiya gaya ho
    # 3. Bot ka naam liya gaya ho
    # 4. (Optional) Har message pe reply chahiye toh niche 'True' add kar dein
    
    if is_private or is_reply_to_me or is_mentioned:
        if not message.text: return
        
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        api_reply = await get_api_reply(user_id, user_text)
        
        if api_reply:
            final_text = make_female_tone(api_reply)
            chat_lang = get_chat_language(chat_id)
            if chat_lang not in ["hi", "en", "nolang"]:
                try:
                    final_text = GoogleTranslator(source='auto', target=chat_lang).translate(final_text)
                except: pass
            
            await message.reply_text(final_text)

# --- Chatbot Toggle Command ---
@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Admin only! ❌")

    status = "Enabled ✅"
    curr = status_db.find_one({"chat_id": message.chat.id})
    if curr and curr.get("status") == "disabled":
        status = "Disabled ❌"

    buttons = [[
        InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
        InlineKeyboardButton("Disable", callback_data="disable_chatbot")
    ]]
    await message.reply_text(f"**Chatbot Status:** {status}", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Mana kiya na!", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ Chatbot now **{action}d**!")
