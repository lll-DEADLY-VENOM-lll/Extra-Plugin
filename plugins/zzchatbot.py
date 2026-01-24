# ======================================================
# ©️ 2025-30 All Rights Reserved by Revange ⚡
# 🛡️ ChatBot Version: 10.0 [Master Jugaad - No API Key]
# 🧑‍💻 Developer: t.me/dmcatelegram
# =======================================================

import random
import re
import requests
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import MONGO_DB_URI as MONGO_URL
from VIPMUSIC import app as nexichat

# Database Setup
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]

# --- FEMALE & RESPECT FILTER ---
def make_female_and_polite(text):
    """Jawab ko ladki jaisa aur izzatdar banane ka jugaad"""
    # Male words ko Female mein badalna
    replacements = {
        "karta hoon": "karti hoon",
        "karta hu": "karti hu",
        "raha hoon": "rahi hoon",
        "raha hu": "rahi hu",
        "gaya tha": "gayi thi",
        "aaunga": "aaungi",
        "karunga": "karungi",
        "bhai": "ji",
        "tu ": "aap ",
        "tera": "aapka",
        "tujhe": "aapko",
        "pagal": "pagli",
        "ladka": "ladki"
    }
    for male, female in replacements.items():
        text = re.sub(f"\\b{male}\\b", female, text, flags=re.IGNORECASE)
    
    # Extra izzat add karna agar "aap" na ho
    if "aap" not in text.lower() and "ji" not in text.lower():
        text = text + " ji"
    return text

# --- COMMANDS ---

@nexichat.on_message(filters.command("chatbot"))
async def chaton(client, message):
    buttons = [[
        InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="enable_chatbot"),
        InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="disable_chatbot")
    ]]
    await message.reply_text(
        "🤖 **Master Chatbot Settings**\n\nAb main bina kisi API key ke har message ka reply dungi! ✨",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# --- CHATTING LOGIC (NO API KEY NEEDED) ---

@nexichat.on_message(filters.text & ~filters.bot)
async def jugaad_chatbot_response(client: Client, message: Message):
    # 1. Check if Enabled
    chat_status = status_db.find_one({"chat_id": message.chat.id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Ignore Commands
    if message.text.startswith(("/", "!", ".")):
        return

    try:
        # Show Typing Action
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # --- JUGAAD API (Public Free API) ---
        # Yeh API bina key ke chalti hai
        user_msg = message.text
        api_url = f"https://api.simsimi.net/v2/?text={user_msg}&lc=hi" # Hindi/Hinglish Support
        
        response = requests.get(api_url, timeout=10)
        data = response.json()
        
        # API se reply nikalna
        if "success" in data:
            raw_reply = data["success"]
        else:
            # Fallback agar simsimi fail ho
            raw_reply = "Ji? Main samajh nahi paayi."

        # 3. Apply Female & Respect Tone
        final_reply = make_female_and_polite(raw_reply)

        # 4. Final Reply
        if final_reply:
            await message.reply_text(final_reply)
            
    except Exception as e:
        print(f"Jugaad Error: {e}")
        # Agar kuch bhi kaam na kare toh chota sa reply
        if message.chat.type == "private":
            await message.reply_text("Ji, aapne kya kaha? ✨")

# --- CALLBACK HANDLERS ---
@nexichat.on_callback_query(filters.regex(r"enable_chatbot|disable_chatbot"))
async def cb_handler(client, query):
    chat_id = query.message.chat.id
    if query.data == "enable_chatbot":
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await query.answer("Chatbot Enabled!")
        await query.edit_message_text("✅ **Chatbot Active!**\nAb main sabka reply karungi ek ladki ki tarah. ✨")
    else:
        status_db.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await query.answer("Chatbot Disabled!")
        await query.edit_message_text("❌ **Chatbot Disabled.**")

# ======================================================
# 🚀 MASTER JUGAAD MODULE LOADED (FREE & FEMALE TONE)
# ======================================================
