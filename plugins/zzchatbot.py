import re
import random
import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

# --- Configuration ---
from config import MONGO_DB_URI as MONGO_URL
from config import API_ID, API_HASH, BOT_TOKEN
import config

# Gemini API Key
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", "AIzaSyBxwcxTICnoLHp9iLOc_c83V_Wf3IaG-8I")

from VIPMUSIC import app as nexichat

# --- AI Configuration ---
genai.configure(api_key=GEMINI_API_KEY)

# Aaru Personality
SYSTEM_INSTRUCTION = (
    "Your name is Aaru. You are a sweet, bubbly Indian girl. Speak in Hinglish (Hindi + English). "
    "Use emojis like 🌸, ✨, 😊, ❤️. Respond as a female (e.g., 'main kar rahi hoon'). "
    "Keep answers short and human-like. Don't mention you are an AI."
)

# --- MongoDB Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["AaruAI_DB"]["StatusCollection"]

# --- Abuse Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod", "loda", "lavda"]

# --- Smart AI Logic (Fixes 404 Error) ---
async def get_aaru_reply(user_text):
    # Alag-alag models try karega agar ek fail ho jaye
    models_to_try = ["gemini-1.5-flash", "gemini-pro"]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION
            )
            response = model.generate_content(user_text)
            return response.text
        except Exception as e:
            print(f"Model {model_name} error: {e}")
            continue # Agla model try karega
            
    return "Uff.. mera dimaag thoda thak gaya hai, baad mein baat karein? 🌸"

# --- Admin Check Helper ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# --- Main Chatbot Logic (Fixes AttributeError) ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def aaru_ai_handler(client: Client, message: Message):
    chat_id = message.chat.id
    user_text = message.text if message.text else ""

    # 1. Skip Commands
    if user_text.startswith(("/", "!", ".")):
        return

    # 2. Status Check
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 3. Abuse Filter
    if any(word in user_text.lower() for word in ABUSIVE_WORDS):
        return await message.reply_text("Gandi baat nahi! Tameez se bolo. 😡")

    # 4. Trigger Check (Fixed AttributeError here)
    is_private = message.chat.type.value == "private"
    
    # Check if replied to bot
    is_reply_to_me = False
    if message.reply_to_message:
        # Check if reply_to_message has a user (avoids NoneType error)
        if message.reply_to_message.from_user:
            bot_me = await client.get_me()
            if message.reply_to_message.from_user.id == bot_me.id:
                is_reply_to_me = True
    
    # Keywords
    keywords = ["aaru", "hi", "hello", "suno", "kaise ho"]
    is_keyword = any(re.search(rf"\b{word}\b", user_text.lower()) for word in keywords)

    # Execute
    if is_private or is_reply_to_me or is_keyword:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        reply = await get_aaru_reply(user_text)
        if reply:
            await message.reply_text(reply)

# --- Settings Command ---

@nexichat.on_message(filters.command(["chatbot", "aaru"]))
async def chatbot_settings(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi ye kar sakte hain! ❌")

    curr = status_db.find_one({"chat_id": message.chat.id})
    status = "Disabled ❌" if curr and curr.get("status") == "disabled" else "Enabled ✅"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Enable ✅", callback_data="enable_aaru"),
        InlineKeyboardButton("Disable ❌", callback_data="disable_aaru")
    ]])

    await message.reply_text(
        f"<b>🌸 Aaru AI Chatbot Settings</b>\n<b>Status:</b> {status}",
        reply_markup=keyboard
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_aaru$"))
async def update_status(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Access Denied! ⛔", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ **Aaru AI** ab is chat mein **{action}d** hai!")
