from VIPMUSIC import app, CHATBOT_GROUP
from VIPMUSIC.database.chatbotdb import enable_chatbot, disable_chatbot, is_chatbot_enabled
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config import config 
from VIPMUSIC.decorator.chatadmin import chatadmin
from pyrogram.enums import ChatAction
import httpx  
import re
import random
from VIPMUSIC.decorator.save import save 
from VIPMUSIC.decorator.errors import error

# --- Female Tone Logic (Zoya Touch) ---
def make_female_tone(text):
    replacements = {
        r"\braha hoon\b": "rahi hoon",
        r"\braha tha\b": "rahi thi",
        r"\bgaya\b": "gayi",
        r"\bbhai\b": "behen 🌸",
        r"\bhoon\b": "hoon ji ✨",
        r"\bpagal\b": "pagli 🙈"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# Command to toggle status (No changes here, it's perfect)
@app.on_message(filters.command("chatbot", prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def chatbot_handler(client: Client, message: Message):
    chat_id = message.chat.id
    if await is_chatbot_enabled(chat_id):
        button = InlineKeyboardMarkup([[InlineKeyboardButton("🔴 Disable ChatBot", callback_data=f"disable_chatbot:{chat_id}")]])
        await message.reply_text("**📢 ChatBot is currently ENABLED.**", reply_markup=button)
    else:
        button = InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Enable ChatBot", callback_data=f"enable_chatbot:{chat_id}")]])
        await message.reply_text("**📢 ChatBot is currently DISABLED.**", reply_markup=button)

# Callback handler (No changes needed)
@app.on_callback_query(filters.regex("^(enable_chatbot|disable_chatbot):"))
@chatadmin
@error
async def toggle_announcements(client: Client, callback_query: CallbackQuery):
    action, chat_id = callback_query.data.split(":")
    chat_id = int(chat_id)
    if action == "enable_chatbot":
        await enable_chatbot(chat_id, "ChatBot", "Enabled")
        await callback_query.message.edit_text("**🟢 ChatBot Enabled!**")
    else:
        await disable_chatbot(chat_id)
        await callback_query.message.edit_text("**🔴 ChatBot Disabled!**")

# --- Modified Message Handler (The Core Fix) ---
@app.on_message(filters.group | filters.private, group=CHATBOT_GROUP)
@error
@save
async def handle_chatbot(client: Client, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    if not await is_chatbot_enabled(message.chat.id):
        return    

    # Trigger conditions
    me = await client.get_me()
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == me.id
    is_mentioned = message.text and (f"@{me.username}" in message.text or me.first_name.lower() in message.text.lower())
    
    if message.chat.type.value == "private" or is_reply_to_me or is_mentioned:
        await client.send_chat_action(message.chat.id, action=ChatAction.TYPING)
        user_input = message.text or "hi"
        
        # Modern Stable API (Brainshop ki jagah ye use karein)
        api_url = f"https://api.punjabistatus.in/chat?msg={user_input}"

        try:
            async with httpx.AsyncClient(timeout=15) as session:
                response = await session.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    # API response nikalna (adjust based on actual json key)
                    bot_response = data.get("response") or data.get("reply")
                    
                    if bot_response:
                        # Zoya ki voice mein change karo
                        final_text = make_female_tone(bot_response)
                        await message.reply_text(final_text)
                    else:
                        await message.reply_text("Uff.. kuch samajh nahi aaya. Fir se bolo? 🌸")
                else:
                    # Fallback agar API down ho
                    await message.reply_text("Mood thoda off hai mera, baad mein baat karein? ✨")
        except Exception as e:
            print(f"Chatbot Error: {e}")
            # Silent error taaki bot baar baar disable na ho

__module__ = "Chatbot"
__help__ = "✧ /chatbot : Enable or Disable chatbot in your group."
