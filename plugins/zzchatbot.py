import random
import re
import aiohttp
from urllib.parse import quote
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]

# --- New Working APIs (Stable) ---
# 1. SimSimi API (Hindi ke liye sabse best aur stable)
API_HINDI = "https://api.simsimi.vn/v2/simsimi?text={}&lc=hi"
# 2. Alternative Chat API (Backup)
API_BACKUP = "https://api.vkrtools.in/api/chatbot?msg={}&name=Zoya&master=Vishal"

# --- Advanced Female Tone Logic ---
def make_female_tone(text):
    if not text: return text
    # Words to replace for feminine touch
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
        r"\bhoon\b": "hoon ji ✨",
        r"\bkaise ho\b": "kaise ho ji?",
        r"\bbol raha hai\b": "bol rahi hai"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Adding emojis to make it look like a girl's chat
    if not any(e in text for e in ["🌸", "✨", "🙈", "😘", "😊"]):
        emojis = [" 🌸", " ✨", " 🙈", " 😊"]
        text += random.choice(emojis)
        
    return text

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# --- Multi-API Fetcher ---
async def get_working_reply(text):
    msg = quote(text)
    async with aiohttp.ClientSession() as session:
        # Step 1: SimSimi (Very fast for Hindi)
        try:
            async with session.get(API_HINDI.format(msg), timeout=5) as r1:
                if r1.status == 200:
                    data = await r1.json()
                    if data.get("result"):
                        return data.get("result")
        except: pass

        # Step 2: VKR API (Backup)
        try:
            async with session.get(API_BACKUP.format(msg), timeout=5) as r2:
                if r2.status == 200:
                    data = await r2.json()
                    if data.get("status") == "success":
                        return data.get("reply")
        except: pass
        
    return None

# --- Main Message Handler ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    
    # 1. Chatbot Status Check (Enabled/Disabled)
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip Commands
    if message.text and message.text.startswith(("/", "!", ".")):
        return

    # 3. Trigger Conditions (Private chat, Tag, or Reply)
    me = await client.get_me()
    is_private = message.chat.type.value == "private"
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id
    is_mentioned = message.text and (f"@{me.username}" in message.text or me.first_name.lower() in message.text.lower())

    if is_private or is_reply_to_me or is_mentioned:
        if not message.text: return
        
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # API se reply lena
        raw_reply = await get_working_reply(message.text)
        
        if raw_reply:
            # Female tone convert karna
            final_text = make_female_tone(raw_reply)
            await message.reply_text(final_text)
        else:
            # All APIs failed fallback
            if is_private:
                await message.reply_text("Aww.. abhi mera network thoda slow hai, thodi der baad baat karte hain? 🌸")

# --- Admin Controls ---

@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi chatbot control kar sakte hain! ❌")

    status = "Enabled ✅"
    curr = status_db.find_one({"chat_id": message.chat.id})
    if curr and curr.get("status") == "disabled":
        status = "Disabled ❌"

    buttons = [[
        InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
        InlineKeyboardButton("Disable", callback_data="disable_chatbot")
    ]]
    await message.reply_text(f"**Zoya Chatbot Settings**\n\nAbhi ka status: {status}\n\nNiche diye buttons se on/off karein:", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Aapke paas permission nahi hai!", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ Chatbot ab **{action}d** ho gaya hai is group ke liye!")
