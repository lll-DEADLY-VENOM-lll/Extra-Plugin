import random
import re
import asyncio
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from deep_translator import GoogleTranslator 
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

chatdb = MongoClient(MONGO_URL)
worddb = MongoClient(WORD_MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
chatai = worddb["Word"]["WordDb"] 
lang_db = chatdb["ChatLangDb"]["LangCollection"]
bio_db = chatdb["ChatBioDb"]["BioSettings"] # Naya database bio settings ke liye

__MODULE__ = "Chatbot"
__HELP__ = """
<b>Chatbot Commands:</b>
• /chatbot - Chatbot settings toggle (Enable/Disable).
• /biolink on - Bio mein link rakhne waalo ke messages delete karein.
• /biolink off - Sabko message karne ki ijazat de (Free mode).

<b>Features:</b>
• New member welcome.
• Auto link deleter in messages.
• Female tone chatbot.
• Abuse filter.
• Profile Bio link protection.
"""

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

def make_female_tone(text):
    replacements = {
        r"\braha hoon\b": "rahi hoon", r"\braha tha\b": "rahi thi",
        r"\braha hai\b": "rahi hai", r"\bgaya tha\b": "gayi thi",
        r"\bgaya\b": "gayi", r"\btha\b": "thi",
        r"\bbhai\b": "behen 🌸", r"\bbhaiya\b": "didi",
        r"\bhoon\b": "hoon ji ✨"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod"]

# ==========================================
# 1. BIO-LINK PROTECTION (The "Free/Unfree" logic)
# ==========================================
@nexichat.on_message(filters.group & ~filters.bot, group=1)
async def bio_and_link_guard(client: Client, message: Message):
    if not message.from_user: return
    
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Admin ko check karne ki zaroorat nahi
    if await is_admin(client, chat_id, user_id):
        return

    # A. Check for link in Message Text
    link_pattern = r"(https?://)?(t\.me|telegram\.me|telegram\.dog)/[a-zA-Z0-9_]+"
    if message.text and re.search(link_pattern, message.text):
        try:
            await message.delete()
            warn = await message.reply_text(f"⚠️ {message.from_user.mention}, Links allow nahi hain!")
            await asyncio.sleep(4)
            return await warn.delete()
        except: return

    # B. Check for link in Profile BIO (Free/Unfree Logic)
    # Check if Bio Protection is ON for this group
    bio_check = bio_db.find_one({"chat_id": chat_id})
    if bio_check and bio_check.get("status") == "on":
        try:
            # User ki profile fetch karna
            user_info = await client.get_chat(user_id)
            bio_text = user_info.bio or ""
            
            if re.search(link_pattern, bio_text):
                await message.delete()
                warn = await message.reply_text(f"🚫 {message.from_user.mention}, Aapke Bio mein link hai. Pehle use hatayein tabhi message kar payenge.")
                await asyncio.sleep(4)
                await warn.delete()
        except Exception:
            pass

# ==========================================
# 2. BIO PROTECTION TOGGLE COMMANDS
# ==========================================
@nexichat.on_message(filters.command("biolink") & filters.group)
async def set_bio_mode(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins ye command use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/biolink on` (Delete messages) ya `/biolink off` (Free mode)")

    choice = message.command[1].lower()
    if choice == "on":
        bio_db.update_one({"chat_id": message.chat.id}, {"$set": {"status": "on"}}, upsert=True)
        await message.reply_text("✅ Bio-Link Protection **ON**! Ab jin logon ke bio mein link hoga, unke message delete ho jayenge.")
    elif choice == "off":
        bio_db.update_one({"chat_id": message.chat.id}, {"$set": {"status": "off"}}, upsert=True)
        await message.reply_text("✅ Bio-Link Protection **OFF** (Free)! Ab sab message kar sakte hain.")
    else:
        await message.reply_text("Invalid option! Use 'on' or 'off'.")

# ==========================================
# 3. NEW MEMBER WELCOME
# ==========================================
@nexichat.on_message(filters.new_chat_members)
async def welcome_member(client: Client, message: Message):
    for member in message.new_chat_members:
        if member.id == (await client.get_me()).id: continue
        await message.reply_text(f"Swagat hai {member.mention} ji! 🌸\nGroup mein masti karo par tameez se. 😊")

# ==========================================
# 4. CHATBOT LOGIC
# ==========================================
@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    user_text = message.text.lower() if message.text else ""
    bot_me = await client.get_me()

    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled": return
    if user_text.startswith(("/", "!", ".")): return

    # Abuse Filter
    if any(word in user_text for word in ABUSIVE_WORDS):
        return await message.reply_text("Gandi baat nahi! 😡 Tameez rakhein.")

    # Trigger logic
    is_private = message.chat.type.value == "private"
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == bot_me.id
    is_mentioned = f"@{bot_me.username.lower()}" in user_text or "zoya" in user_text
    
    if is_private or is_reply_to_me or is_mentioned or (random.random() < 0.20):
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        is_chat = list(chatai.find({"word": user_text}))
        if not is_chat:
            is_chat = list(chatai.aggregate([{"$sample": {"size": 1}}]))
        
        if is_chat:
            reply_data = random.choice(is_chat)
            res = make_female_tone(reply_data["text"]) if reply_data.get("check") != "sticker" else reply_data["text"]
            
            if reply_data.get("check") == "sticker":
                await message.reply_sticker(res)
            else:
                await message.reply_text(res)

# --- Admin Command for Chatbot Toggle ---
@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("No Permission! ❌")

    status = "Enabled ✅"
    curr = status_db.find_one({"chat_id": message.chat.id})
    if curr and curr.get("status") == "disabled": status = "Disabled ❌"

    buttons = [[InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
                InlineKeyboardButton("Disable", callback_data="disable_chatbot")]]
    await message.reply_text(f"Chatbot Status: {status}", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Mana kiya na! ⛔", show_alert=True)
    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"Chatbot {action}d successfully!")
