# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 9.0 [Gemini Free AI - Fixed]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import MONGO_DB_URI as MONGO_URL
from VIPMUSIC import app as nexichat

# --- CONFIGURATION ---
# Gemini API Key yahan dalein (Free from: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = "AIzaSyCdjzzyOeCrUmo_9JlXg7Jr7Q5aENXGVHI" 
genai.configure(api_key=GEMINI_API_KEY)

# AI Persona: Female & Respectful
SYSTEM_PROMPT = (
    "Tu ek ladki hai, tera naam Nexi hai. "
    "Tu hamesha bahut tameez aur izzat se baat karti hai. "
    "Tu 'Aap' aur 'Ji' ka istemal karti hai. "
    "Teri bhasha Hinglish (Hindi + English mixed) honi chahiye. "
    "Hamesha ek ladki (female) ki tarah react karna (e.g., karti hoon, rahi hoon)."
)

# Model Setup
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# Database
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]

# --- COMMANDS ---

@nexichat.on_message(filters.command("chatbot"))
async def chaton(client, message):
    buttons = [[
        InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="enable_chatbot"),
        InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="disable_chatbot")
    ]]
    await message.reply_text(
        "🤖 **FREE AI Chatbot Settings**\n\nMain Gemini AI use kar rahi hoon jo bilkul free hai. ✨",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# --- AI CHATTING LOGIC ---

@nexichat.on_message(filters.text & ~filters.bot)
async def ai_chatbot_response(client: Client, message: Message):
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    if message.text.startswith(("/", "!", ".")):
        return

    try:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Start AI Chat
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(message.text)
        
        ai_reply = response.text.strip()

        if ai_reply:
            await message.reply_text(ai_reply)
            
    except Exception as e:
        print(f"AI ERROR: {e}")
        # Agar bot crash ho toh log print hoga par bot chalta rahega

# --- CALLBACK HANDLERS ---
@nexichat.on_callback_query(filters.regex(r"enable_chatbot|disable_chatbot"))
async def cb_handler(client, query):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("AI Chatbot Enabled!")
        await query.edit_message_text("✅ **AI Chatbot Active!** ✨")
    else:
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("AI Chatbot Disabled!")
        await query.edit_message_text("❌ **AI Chatbot Disabled.**")
