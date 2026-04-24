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
# Ye API Safone ki hai, jo ki chatbot ke liye bahut stable hai.
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

# --- API Fetching Logic ---
async def get_api_reply(user_id, word: str):
    try:
        # Message ko encode karna taaki spaces handle ho sakein
        msg = quote(word)
        url = CHAT_API_URL.format(msg, user_id)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # Safone API 'response' key mein reply deti hai
                    return data.get("response")
    except Exception as e:
        print(f"Chat API Error: {e}")
    return None

# --- Chatbot Main Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # 1. Check if bot is disabled in this chat
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip commands
    if message.text and message.text.startswith(("/", "!", ".")):
        return

    # 3. Special Radhe Radhe logic
    if message.text and "radhe" in message.text.lower():
        return await message.reply_text("Radhe Radhe! ✨ Bolo Banke Bihari Lal Ki Jai! 🙏")

    # 4. Trigger Conditions
    is_private = message.chat.type.value == "private"
    is_reply_to_me = False
    if message.reply_to_message:
        me = await client.get_me()
        if message.reply_to_message.from_user.id == me.id:
            is_reply_to_me = True

    user_text = message.text if message.text else ""
    keywords = ["zoya", "bot", "hi", "hello", "hey", "namaste", "sun"]
    is_keyword = any(re.search(rf"\b{word}\b", user_text.lower()) for word in keywords)

    # Bot tabhi reply karega agar private ho, bot ko reply kiya gaya ho, ya keyword ho
    if is_private or is_reply_to_me or is_keyword:
        if not message.text: return # Stickers ignore for now
        
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # API se reply mangwana
        api_reply = await get_api_reply(user_id, user_text)
        
        if api_reply:
            # 1. Female Tone apply karna
            final_text = make_female_tone(api_reply)

            # 2. Language Translation
            chat_lang = get_chat_language(chat_id)
            if chat_lang not in ["hi", "en", "nolang"]:
                try:
                    final_text = GoogleTranslator(source='auto', target=chat_lang).translate(final_text)
                except:
                    pass

            await message.reply_text(final_text)
        else:
            if is_private:
                await message.reply_text("Uff... mera server thoda down lag raha hai, fir se try karna? 🌸")

# --- Admin Commands ---

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
    await message.reply_text(
        f"<b>Chatbot Settings</b>\n\nStatus: {status}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Access Denied! ⛔", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ Chatbot successfully **{action}d**!")
