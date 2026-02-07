import random
import re
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]

WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
worddb = MongoClient(WORD_MONGO_URL)
chatai = worddb["Word"]["WordDb"]

# --- Gali-Galauj Filter (Blacklist) ---
# Yahan aap aur bhi gande shabd add kar sakte hain
BANNED_WORDS = ["gali1", "gali2", "behenchod", "madarchod", "gandu", "loda", "chutiya", "randi"]

def is_respectful(text):
    """Check karta hai ki message mein koi gali to nahi hai."""
    if not text:
        return True
    for word in BANNED_WORDS:
        if re.search(rf"\b{word}\b", text.lower()):
            return False
    return True

# --- Buttons ---
CHATBOT_ON = [
    [
        InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="enable_chatbot"),
        InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="disable_chatbot"),
    ],
]

# --- Commands ---
@nexichat.on_message(filters.command("chatbot") & ~filters.bot)
async def chat_settings(client: Client, message: Message):
    await message.reply_text(
        f"ᴄʜᴀᴛ: {message.chat.title}\n**ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ ᴄʜᴀᴛʙᴏᴛ.**",
        reply_markup=InlineKeyboardMarkup(CHATBOT_ON),
    )

# --- Main Logic ---
@nexichat.on_message((filters.text | filters.sticker | filters.photo | filters.video | filters.audio) & ~filters.bot)
async def chatbot_response(client: Client, message: Message):
    # 1. Chatbot enabled hai ya nahi check karein
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Commands ko ignore karein
    if message.text and any(message.text.startswith(prefix) for prefix in ["!", "/", ".", "?", "@", "#"]):
        return

    # 3. Trigger Condition (Group aur Private dono ke liye)
    bot_id = (await client.get_me()).id
    should_respond = False
    
    if message.chat.type.name == "PRIVATE":
        should_respond = True
    # Group mein: agar bot ko reply kiya gaya ho, tag kiya gaya ho, ya kisi ne kuch likha ho
    elif message.reply_to_message and message.reply_to_message.from_user.id == bot_id:
        should_respond = True
    elif message.text and f"@{client.me.username}" in message.text:
        should_respond = True
    # Niche wali line ko uncomment karein agar aap chahte hain bot group ke HAR message par reply de (Spam ho sakta hai)
    # else: should_respond = True 

    if should_respond:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        query_text = message.text.lower().strip() if message.text else ""
        reply_data = await get_reply(query_text)
        
        if reply_data:
            response_text = reply_data["text"]
            
            # Gali check filter
            if reply_data["check"] == "none" and not is_respectful(response_text):
                response_text = "Main ek accha bot hoon, please ijjat se baat karein. 🙏"

            if reply_data["check"] == "sticker":
                await message.reply_sticker(reply_data["text"])
            elif reply_data["check"] == "photo":
                await message.reply_photo(reply_data["text"])
            elif reply_data["check"] == "video":
                await message.reply_video(reply_data["text"])
            else:
                await message.reply_text(response_text)
        else:
            if message.chat.type.name == "PRIVATE":
                await message.reply_text("Ji, kahiye main aapki kya seva kar sakta hoon? 😊")

    # 4. Learning Logic (Sirf respectful baatein sikhega)
    if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
        if is_respectful(message.text):
            await save_reply(message.reply_to_message, message)

# --- Helper Functions ---
async def save_reply(original_message: Message, reply_message: Message):
    if not original_message.text or not is_respectful(reply_message.text):
        return
        
    word = original_message.text.lower().strip()
    content = None
    check_type = "none"

    if reply_message.sticker:
        content = reply_message.sticker.file_id
        check_type = "sticker"
    elif reply_message.photo:
        content = reply_message.photo.file_id
        check_type = "photo"
    elif reply_message.text:
        content = reply_message.text
        check_type = "none"

    if content:
        exists = chatai.find_one({"word": word, "text": content})
        if not exists:
            chatai.insert_one({"word": word, "text": content, "check": check_type})

async def get_reply(word: str):
    results = list(chatai.find({"word": word}))
    if not results:
        # Kuch random polite messages ka pool
        polite_defaults = [
            {"text": "Ji bilkul!", "check": "none"},
            {"text": "Aap bahut acche hain.", "check": "none"},
            {"text": "Main aapki kaise madad karoon?", "check": "none"}
        ]
        return random.choice(polite_defaults)
    
    return random.choice(results)

# --- Callback Handler ---
@nexichat.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("Chatbot Enabled ✅", show_alert=True)
        await query.edit_message_text(f"**ᴄʜᴀᴛʙᴏᴛ ᴇɴᴀʙʟᴇᴅ!**\nMain hamesha ijjat se baat karunga. 🙏")
    elif query.data == "disable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("Chatbot Disabled ❌", show_alert=True)
        await query.edit_message_text(f"**ᴄʜᴀᴛʙᴏᴛ ᴅɪsᴀʙʟᴇᴅ.**")

__MODULE__ = "ᴄʜᴀᴛʙᴏᴛ"
__HELP__ = "/chatbot - Enable/Disable chatbot with respect filter."
