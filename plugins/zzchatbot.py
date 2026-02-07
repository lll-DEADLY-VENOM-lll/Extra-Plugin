import random
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
# ChatBot Status Database
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]

# Word Database (Learning Database)
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
worddb = MongoClient(WORD_MONGO_URL)
chatai = worddb["Word"]["WordDb"]

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
    # 1. Check if chatbot is disabled for this chat
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Ignore all commands (starting with /, !, etc.)
    if message.text and any(message.text.startswith(prefix) for prefix in ["!", "/", ".", "?", "@", "#"]):
        return

    # 3. Determine if the bot should reply
    # - In Private: Always
    # - In Groups: Only if replied to bot OR bot is mentioned
    bot_info = await client.get_me()
    bot_id = bot_info.id
    bot_username = bot_info.username

    should_respond = False
    if message.chat.type.name == "PRIVATE":
        should_respond = True
    elif message.reply_to_message and message.reply_to_message.from_user.id == bot_id:
        should_respond = True
    elif message.text and f"@{bot_username}" in message.text:
        should_respond = True

    # 4. If triggered, send response
    if should_respond:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        query_text = message.text.lower().strip() if message.text else ""
        reply_data = await get_reply(query_text)
        
        if reply_data:
            if reply_data["check"] == "sticker":
                await message.reply_sticker(reply_data["text"])
            elif reply_data["check"] == "photo":
                await message.reply_photo(reply_data["text"])
            elif reply_data["check"] == "video":
                await message.reply_video(reply_data["text"])
            elif reply_data["check"] == "audio":
                await message.reply_audio(reply_data["text"])
            else:
                await message.reply_text(reply_data["text"])
        else:
            # Optional default reply if nothing found in DB
            if message.chat.type.name == "PRIVATE":
                await message.reply_text("Kuch naya sikhao mujhe, ye samajh nahi aaya!")

    # 5. Learning: Save user replies to build the Hinglish DB
    if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
        await save_reply(message.reply_to_message, message)

# --- Helper Functions ---

async def save_reply(original_message: Message, reply_message: Message):
    """Users ke replies ko database mein save karta hai sikhne ke liye."""
    if not original_message.text:
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
    elif reply_message.video:
        content = reply_message.video.file_id
        check_type = "video"
    elif reply_message.audio:
        content = reply_message.audio.file_id
        check_type = "audio"
    elif reply_message.text:
        content = reply_message.text
        check_type = "none"

    if content:
        # Check if already exists to prevent spamming the same reply
        exists = chatai.find_one({"word": word, "text": content})
        if not exists:
            chatai.insert_one({"word": word, "text": content, "check": check_type})

async def get_reply(word: str):
    """Database se reply dhoondta hai."""
    # Exact match dhoondne ki koshish
    results = list(chatai.find({"word": word}))
    if not results:
        # Agar exact word nahi mila, toh random reply utha lo (Chatty nature ke liye)
        results = list(chatai.aggregate([{ "$sample": { "size": 1 } }]))
    
    if results:
        return random.choice(results)
    return None

# --- Callback Handler ---

@nexichat.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("Chatbot Enabled ✅", show_alert=True)
        await query.edit_message_text(f"**ᴄʜᴀᴛʙᴏᴛ ʜᴀs ʙᴇᴇɴ ᴇɴᴀʙʟᴇᴅ ғᴏʀ {query.message.chat.title}**\n\nAb main Hinglish mein baatein karunga!")

    elif query.data == "disable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("Chatbot Disabled ❌", show_alert=True)
        await query.edit_message_text(f"**ᴄʜᴀᴛʙᴏᴛ ʜᴀs ʙᴇᴇɴ ᴅɪsᴀʙʟᴇᴅ ғᴏʀ {query.message.chat.title}**")

# --- Help Info ---

__MODULE__ = "ᴄʜᴀᴛʙᴏᴛ"
__HELP__ = f"""**
๏ ʜᴇʀᴇ ɪs ᴛʜᴇ ʜᴇʟᴘ ғᴏʀ {nexichat.mention}:

➻ /chatbot - ᴇɴᴀʙʟᴇ ᴏʀ ᴅɪsᴀʙʟᴇ ᴛʜᴇ ᴄʜᴀᴛʙᴏᴛ.
──────────────
📡 **ɴᴏᴛᴇ:** 
- Yeh bot users se seekhta hai (Auto-learning).
- Group mein reply pane ke liye bot ko **reply** karein ya **tag** karein.
- Sirf Hinglish support karta hai.
**"""
