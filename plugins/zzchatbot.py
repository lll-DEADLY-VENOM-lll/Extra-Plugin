# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 7.0 [Fixed Gemini AI + Female Tone]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import random
import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import MONGO_DB_URI as MONGO_URL
from VIPMUSIC import app as nexichat

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyCdjzzyOeCrUmo_9JlXg7Jr7Q5aENXGVHI" # <--- Apni API Key yahan dalein
genai.configure(api_key=GEMINI_API_KEY)

# AI Persona Setup: Yahan hum bot ko 'Female' aur 'Respectful' banate hain
SYSTEM_PROMPT = (
    "Tu ek ladki hai, tera naam Nexi hai. "
    "Tu hamesha bahut tameez aur izzat se baat karti hai. "
    "Tu 'Aap' aur 'Ji' ka istemal karti hai. "
    "Teri bhasha Hinglish (Hindi + English mixed) honi chahiye. "
    "Agar koi gaali de ya badtameezi kare, toh politely bolna ki 'Aap tameez se baat kijiye'. "
    "Hamesha ek ladki (female) ki tarah react karna. "
    "Short aur pyare answers dena."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Updated & Stable Model
    system_instruction=SYSTEM_PROMPT
)

# Database Setup
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]

# --- BUTTONS ---
CHATBOT_ON = [[
    InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="enable_chatbot"),
    InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="disable_chatbot")
]]

# --- COMMANDS ---

@nexichat.on_message(filters.command("chatbot"))
async def chaton(client, message):
    await message.reply_text(
        f"🤖 **AI Chatbot Settings**\n\nMain abhi **Gemini AI** mode mein hoon.\nMain group ke har message ka reply de sakti hoon.",
        reply_markup=InlineKeyboardMarkup(CHATBOT_ON),
    )

# --- AI CHATTING LOGIC ---

@nexichat.on_message(filters.text & ~filters.bot)
async def ai_chatbot_response(client: Client, message: Message):
    # 1. Check if chatbot is enabled for this chat
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Ignore Commands (/, !, .)
    if message.text.startswith(("/", "!", ".")):
        return

    # 3. AI Processing
    try:
        # Show Typing Action
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Send prompt to Gemini
        user_input = message.text
        response = model.generate_content(user_input)
        
        # Get AI text result
        ai_reply = response.text.strip()

        if ai_reply:
            # Bina tag/reply ke seedha group mein message bhejna
            await message.reply_text(ai_reply)
            
    except Exception as e:
        print(f"AI ERROR: {e}")
        # Fallback agar API limit exceed ho ya koi error aaye
        if message.chat.type == ChatType.PRIVATE:
            await message.reply_text("Ji, abhi main thoda busy hoon, baad mein baat karte hain! ✨")

# --- CALLBACK HANDLERS ---
@nexichat.on_callback_query(filters.regex(r"enable_chatbot|disable_chatbot"))
async def cb_handler(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("AI Chatbot Enabled!")
        await query.edit_message_text("✅ **AI Chatbot Active!**\nAb main is group mein sabse baatein karungi. ✨")
    elif query.data == "disable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("AI Chatbot Disabled!")
        await query.edit_message_text("❌ **AI Chatbot Disabled.**\nAb main group mein reply nahi karungi.")

# ======================================================
# 🚀 CORRECTED GEMINI AI MODULE LOADED
# ======================================================
