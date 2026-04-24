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

# --- Highly Stable APIs (No Keys Needed) ---
# 1. Popcat API (Saalon se stable hai)
API_STABLE = "https://api.popcat.xyz/chatbot?msg={}&owner=Vishal&botname=Zoya"
# 2. Hercai API (Modern AI Model)
API_BACKUP = "https://hercai.onrender.com/v3/hercai?question={}"

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

# --- Fetcher with Double Fallback ---
async def get_working_reply(text):
    msg = quote(text)
    async with aiohttp.ClientSession() as session:
        # Step 1: Popcat API try karein (Very Stable)
        try:
            async with session.get(API_STABLE.format(msg), timeout=8) as r1:
                if r1.status == 200:
                    data = await r1.json()
                    return data.get("response")
        except: pass

        # Step 2: Hercai API try karein (Backup)
        try:
            async with session.get(API_BACKUP.format(msg), timeout=8) as r2:
                if r2.status == 200:
                    data = await r2.json()
                    return data.get("reply")
        except: pass
    return None

# --- Main Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    
    # 1. Status Check
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip Commands
    if message.text and message.text.startswith(("/", "!", ".")):
        return

    # 3. Trigger Conditions
    me = await client.get_me()
    is_private = message.chat.type.value == "private"
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id
    is_mentioned = message.text and (f"@{me.username}" in message.text or me.first_name.lower() in message.text.lower())

    if is_private or is_reply_to_me or is_mentioned:
        if not message.text: return
        
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # Working API se reply mangwana
        raw_reply = await get_working_reply(message.text)
        
        if raw_reply:
            # 1. Female Tone apply karna
            final_text = make_female_tone(raw_reply)

            # 2. Translation (Kyunki ye APIs English mein hoti hain)
            chat_lang = get_chat_language(chat_id)
            if chat_lang not in ["nolang"]: # Default Hindi/Any
                try:
                    # Translate to chat's preferred language (Default hi)
                    target = chat_lang if chat_lang != "en" else "en"
                    final_text = GoogleTranslator(source='auto', target=target).translate(final_text)
                except: pass
            
            await message.reply_text(final_text)
        else:
            if is_private:
                await message.reply_text("Uff... abhi mood thoda off hai, baad mein baat karein? 🌸")

# --- Admin Controls ---

@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi use kar sakte hain! ❌")

    status = "Enabled ✅"
    curr = status_db.find_one({"chat_id": message.chat.id})
    if curr and curr.get("status") == "disabled":
        status = "Disabled ❌"

    buttons = [[
        InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
        InlineKeyboardButton("Disable", callback_data="disable_chatbot")
    ]]
    await message.reply_text(f"**Chatbot Settings**\n\nStatus: {status}", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Access Denied!", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ Chatbot successfully **{action}d**!")
