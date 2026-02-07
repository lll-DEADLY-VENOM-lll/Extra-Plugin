import re
import random
import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

# --- Configuration (Aapne hisab se change karein) ---
from config import MONGO_DB_URI as MONGO_URL
from config import API_ID, API_HASH, BOT_TOKEN
import config

# Gemini API Key yahan dalein
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", "AIzaSyBxwcxTICnoLHp9iLOc_c83V_Wf3IaG-8I")

# Nexichat instance (Aapka bot client)
from VIPMUSIC import app as nexichat

# --- AI Configuration ---
genai.configure(api_key=GEMINI_API_KEY)

# Aaru ki Personality
SYSTEM_INSTRUCTION = (
    "Your name is Aaru. You are a sweet, bubbly, and very friendly Indian girl. "
    "You speak in Hinglish (mix of Hindi and English). Use emojis like 🌸, ✨, 😊, ❤️, 🙈. "
    "Always respond as a girl (use 'main kar rahi hoon', 'main thak gayi' etc). "
    "If someone asks who created you, say 'Mujhe mere master ne banaya hai'. "
    "Keep your answers short, sweet, and human-like. Don't be formal like a bot."
)

# AI Model Setup with Error Handling
try:
    # Latest Model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_INSTRUCTION
    )
except Exception:
    # Fallback if 1.5-flash is not available
    model = genai.GenerativeModel('gemini-pro')

# --- MongoDB Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["AaruAI_DB"]["StatusCollection"]

# --- Gali Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod", "loda", "lavda"]

# --- Helpers ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

async def get_aaru_reply(user_text):
    try:
        # AI se jawab mangna
        response = model.generate_content(user_text)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        # Agar error aaye toh ek cute sa fallback message
        return "Uff.. mera dimaag thoda ghum gaya hai, phir se bolo? 🌸"

# --- Main Bot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def aaru_ai_handler(client: Client, message: Message):
    chat_id = message.chat.id
    user_text = message.text if message.text else ""

    # 1. Skip Commands
    if user_text.startswith(("/", "!", ".")):
        return

    # 2. Check if Chatbot is Disabled
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 3. Abuse Filter
    if any(word in user_text.lower() for word in ABUSIVE_WORDS):
        return await message.reply_text("Gandi baat nahi karte! Tameez se bolo varna baat nahi karungi. 😡")

    # 4. Trigger Conditions
    is_private = message.chat.type.value == "private"
    
    # Check if replied to bot
    is_reply_to_me = False
    if message.reply_to_message:
        bot_me = await client.get_me()
        if message.reply_to_message.from_user.id == bot_me.id:
            is_reply_to_me = True
    
    # Keywords
    keywords = ["aaru", "hi", "hello", "kaise ho", "bot", "suno"]
    is_keyword = any(re.search(rf"\b{word}\b", user_text.lower()) for word in keywords)

    # 5. Reply Execution
    if is_private or is_reply_to_me or is_keyword:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # AI Response
        final_reply = await get_aaru_reply(user_text)
        
        if final_reply:
            await message.reply_text(final_reply)

# --- Admin Controls ---

@nexichat.on_message(filters.command(["chatbot", "aaru"]))
async def chatbot_settings(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi meri settings chhed sakte hain! ❌")

    curr = status_db.find_one({"chat_id": message.chat.id})
    status = "Disabled ❌" if curr and curr.get("status") == "disabled" else "Enabled ✅"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Enable ✅", callback_data="enable_aaru"),
            InlineKeyboardButton("Disable ❌", callback_data="disable_aaru")
        ]
    ])

    await message.reply_text(
        f"<b>🌸 Aaru AI Chatbot Settings</b>\n\n<b>Status:</b> {status}\n\nKya aap mujhe is chat mein on ya off karna chahte hain?",
        reply_markup=keyboard
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_aaru$"))
async def update_status(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Aapko permission nahi hai! ⛔", show_alert=True)

    action = query.data.split("_")[0] # enable or disable
    status_db.update_one(
        {"chat_id": query.message.chat.id}, 
        {"$set": {"status": f"{action}d"}}, 
        upsert=True
    )
    
    await query.edit_message_text(f"✅ **Aaru AI** ab is chat mein **{action}d** ho gayi hai!")
    await query.answer(f"Done: {action}d")
