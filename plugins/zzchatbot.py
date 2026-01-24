# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 8.0 [GPT-4o AI + Female Persona]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import random
from openai import OpenAI
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import MONGO_DB_URI as MONGO_URL
from VIPMUSIC import app as nexichat

# --- CONFIGURATION ---
OPENAI_API_KEY = "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" # <--- Apni GPT API Key yahan dalein
gpt_client = OpenAI(api_key=OPENAI_API_KEY)

# AI Persona: Bot ko ladki aur izzatdar banane ke liye prompt
SYSTEM_PROMPT = (
    "Tu ek Indian ladki hai, tera naam Nexi hai. "
    "Tu hamesha bahut tameez aur pyaarr se baat karti hai. "
    "Tu 'Aap' aur 'Ji' ka istemal karti hai aur 'Bhai' nahi bolti, 'Ji' bolti hai. "
    "Teri language Hinglish (Hindi + English mixed) hai. "
    "Agar koi gaali de toh gussa mat karna, bas kehna 'Aap tameez se baat kijiye please'. "
    "Tu hamesha female (ladki) ki tarah baat karegi, jaise: 'karti hoon', 'khati hoon', 'rahi hoon'."
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
        f"🤖 **GPT AI Chatbot Settings**\n\nMain abhi **GPT-4o** mode mein hoon.\nMain group mein har kisi ko izzat se reply karungi. ✨",
        reply_markup=InlineKeyboardMarkup(CHATBOT_ON),
    )

# --- GPT AI CHATTING LOGIC ---

@nexichat.on_message(filters.text & ~filters.bot)
async def gpt_chatbot_response(client: Client, message: Message):
    # 1. Check Status (Enabled hai ya nahi)
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Ignore Commands
    if message.text.startswith(("/", "!", ".")):
        return

    # 3. GPT AI Processing
    try:
        # Show Typing...
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # GPT API Request
        response = gpt_client.chat.completions.create(
            model="gpt-4o-mini", # Fast and smart model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            max_tokens=200, # Chote aur pyare jawab ke liye
            temperature=0.7
        )
        
        ai_reply = response.choices[0].message.content.strip()

        if ai_reply:
            # Seedha reply dena bina tag kiye
            await message.reply_text(ai_reply)
            
    except Exception as e:
        print(f"GPT ERROR: {e}")
        # Error fallback
        if message.chat.type == ChatType.PRIVATE:
            await message.reply_text("Maaf kijiye ji, abhi mera server thoda thak gaya hai. ✨")

# --- CALLBACK HANDLERS ---
@nexichat.on_callback_query(filters.regex(r"enable_chatbot|disable_chatbot"))
async def cb_handler(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("GPT Chatbot Enabled!")
        await query.edit_message_text("✅ **GPT AI Chatbot Active!**\nAb main is group mein sabse pyaar se baatein karungi. 🌸")
    elif query.data == "disable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("GPT Chatbot Disabled!")
        await query.edit_message_text("❌ **GPT AI Chatbot Disabled.**")

# ======================================================
# 🚀 GPT-POWERED AI MODULE LOADED (FEMALE PERSONA)
# ======================================================
