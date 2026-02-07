import re
import random
import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

# --- Configuration ---
# Note: In sabko aap apni config.py file mein bhi rakh sakte hain
from config import MONGO_DB_URI as MONGO_URL
from config import API_ID, API_HASH, BOT_TOKEN
import config

# Gemini API Key yahan dalein (Get it from: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", "AIzaSyBxwcxTICnoLHp9iLOc_c83V_Wf3IaG-8I")

from VIPMUSIC import app as nexichat

# --- Google Gemini AI Setup ---
genai.configure(api_key=GEMINI_API_KEY)

# Aaru ki Personality define karna
SYSTEM_INSTRUCTION = (
    "Your name is Aaru. You are a sweet, bubbly, and friendly Indian girl. "
    "Speak in Hinglish (Hindi + English mix). Use emojis like 🌸, ✨, 😊, ❤️, 🙈. "
    "Always respond as a female (e.g., use 'kar rahi hoon', 'kha liya' instead of 'raha hoon'). "
    "If someone asks who created you, say 'Mujhe mere master ne banaya hai'. "
    "Keep your answers natural, short, and very human-like. Don't act like a search engine."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- Database Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["AaruBotDB"]["StatusCollection"]

# --- Abuse Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod", "loda"]

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True # Private chat
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

async def get_aaru_response(user_input):
    try:
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(user_input)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "Uff.. mera dimaag thoda thak gaya hai, baad mein baat karein? 🌸"

# --- Main Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def aaru_chatbot(client: Client, message: Message):
    chat_id = message.chat.id
    user_text = message.text if message.text else ""
    
    # 1. Check Chatbot Status (Enabled/Disabled)
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip Commands
    if user_text.startswith(("/", "!", ".")):
        return

    # 3. Toxicity Filter
    if any(word in user_text.lower() for word in ABUSIVE_WORDS):
        return await message.reply_text("Gandi baat nahi karte! Tameez se bolo varna main baat nahi karungi. 😡")

    # 4. Define Triggers
    is_private = message.chat.type.value == "private"
    
    # Reply logic
    is_reply_to_me = False
    if message.reply_to_message:
        bot_id = (await client.get_me()).id
        if message.reply_to_message.from_user.id == bot_id:
            is_reply_to_me = True
    
    # Keyword triggers
    keywords = ["aaru", "hi", "hello", "suno", "kaise ho", "bot"]
    is_keyword = any(re.search(rf"\b{word}\b", user_text.lower()) for word in keywords)

    # Trigger Execution
    if is_private or is_reply_to_me or is_keyword:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # Get AI Response
        response = await get_aaru_response(user_text)
        
        if response:
            await message.reply_text(response)

# --- Admin Commands ---

@nexichat.on_message(filters.command(["chatbot", "aaru"]))
async def toggle_aaru(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi meri settings badal sakte hain! ❌")

    # Current status check
    curr = status_db.find_one({"chat_id": message.chat.id})
    status_text = "Disabled ❌" if curr and curr.get("status") == "disabled" else "Enabled ✅"

    buttons = [[
        InlineKeyboardButton("Enable ✅", callback_data="enable_aaru"),
        InlineKeyboardButton("Disable ❌", callback_data="disable_aaru")
    ]]
    
    await message.reply_text(
        f"<b>🌸 Aaru AI Chatbot Settings</b>\n\n<b>Current Status:</b> {status_text}\n\nAap niche diye gaye buttons se mujhe manage kar sakte hain.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_aaru$"))
async def status_callback(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Aapko permission nahi hai! ⛔", show_alert=True)

    action = query.data.split("_")[0] # enable or disable
    status_db.update_one(
        {"chat_id": query.message.chat.id}, 
        {"$set": {"status": f"{action}d"}}, 
        upsert=True
    )
    
    await query.edit_message_text(f"✅ **Aaru AI Chatbot** ab is chat mein **{action}d** kar diya gaya hai!")
    await query.answer(f"Chatbot {action}d!", show_alert=False)
