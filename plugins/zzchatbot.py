# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 6.0 [Real AI + Female Persona]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import random
import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import MONGO_DB_URI as MONGO_URL
from VIPMUSIC import app as nexichat

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyCdjzzyOeCrUmo_9JlXg7Jr7Q5aENXGVHI" # <--- Apni API Key yahan dalein
genai.configure(api_key=GEMINI_API_KEY)

# AI Model Setup (Female & Polite Persona)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="Your name is Nexi. You are a kind, respectful, and helpful female AI. "
                       "Always speak politely. Use 'ji' and 'aap'. Reply in Hinglish. "
                       "If someone abuses, politely refuse to talk. Keep your tone sweet and feminine."
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
        f"🤖 **AI Chatbot Settings**\n\nAb main asli AI se baatein karungi!",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# --- REAL AI CHATTING LOGIC ---

@nexichat.on_message(filters.text & ~filters.bot)
async def ai_chatbot_response(client: Client, message: Message):
    # 1. Check Status
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Ignore Commands
    if message.text.startswith(("/", "!", ".")):
        return

    # 3. Trigger Logic (Group mein bina tag ke reply karega)
    # Hum chahte hain ki bot har message par reply kare
    try:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # AI se response mangna
        prompt = message.text
        response = model.generate_content(prompt)
        ai_text = response.text

        # Izzat aur Female tone ensure karna (Filter)
        # Gemini system instruction se pehle hi handle kar lega, 
        # phir bhi extra safety ke liye hum reply bhejte hain.
        
        if ai_text:
            await message.reply_text(ai_text)
            
    except Exception as e:
        print(f"AI Error: {e}")
        # Agar AI fail ho jaye toh normal reply
        if message.chat.type == ChatType.PRIVATE:
            await message.reply_text("Maaf kijiyega ji, abhi mera server thoda busy hai. ✨")

# --- CALLBACK HANDLERS ---
@nexichat.on_callback_query(filters.regex(r"enable_chatbot|disable_chatbot"))
async def cb_handler(client, query):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.edit_message_text("✅ **AI Chatbot Active! Main ab sabse baatein karungi.**")
    else:
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.edit_message_text("❌ **AI Chatbot Disabled.**")

# ======================================================
# 🚀 NEXT-GEN REAL AI LOADED (FEMALE PERSONA)
# ======================================================
