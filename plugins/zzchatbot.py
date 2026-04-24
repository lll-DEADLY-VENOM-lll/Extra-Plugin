import random
import re
import aiohttp
import google.generativeai as genai
from urllib.parse import quote
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from deep_translator import GoogleTranslator 
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- API Keys Configuration ---
# Gemini API Key yahan dalein (Free from: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = "AIzaSyBxwcxTICnoLHp9iLOc_c83V_Wf3IaG-8I" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- Database Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# --- Female Tone Instruction ---
# Gemini ko instruct karne ke liye instruction string
SYSTEM_INSTRUCTION = "Tu ek cute Indian ladki hai jiska naam Zoya hai. Hamesha ladkiyon ki tarah baat kar (jaise 'main kar rahi hoon', 'kha rahi hoon'). Hindi aur English mix use kar (Hinglish). Short aur sweet jawab de."

# --- Regex for extra safety (Manual Tone) ---
def make_female_tone(text):
    if not text: return text
    replacements = {
        r"\braha hoon\b": "rahi hoon",
        r"\braha tha\b": "rahi thi",
        r"\bgaya tha\b": "gayi thi",
        r"\bgaya\b": "gayi",
        r"\bbhai\b": "behen 🌸",
        r"\bhoon\b": "hoon ji ✨"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# --- Gemini API Logic ---
async def get_gemini_response(user_input):
    try:
        # Prompt mein system instruction add kar rahe hain taaki tone female rahe
        prompt = f"{SYSTEM_INSTRUCTION}\n\nUser: {user_input}\nZoya:"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else "hi"

# --- Main Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    
    # 1. Status Check
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip Commands
    if message.text and message.text.startswith(("/", "!", ".")):
        return

    # 3. Trigger Conditions
    me = await client.get_me()
    is_private = message.chat.type.value == "private"
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id
    is_mentioned = message.text and (f"@{me.username}" in message.text or me.first_name.lower() in message.text.lower())

    if is_private or is_reply_to_me or is_mentioned:
        if not message.text: return
        
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # Gemini AI se response lena
        raw_reply = await get_gemini_response(message.text)
        
        if raw_reply:
            # Tone final check
            final_text = make_female_tone(raw_reply)
            await message.reply_text(final_text)
        else:
            # Agar Gemini bhi fail ho jaye toh default message
            if is_private:
                await message.reply_text("Uff... mera mood thoda off hai, baad mein baat karein? 🌸")

# --- Admin Controls (Same as before) ---
@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi use kar sakte hain! ❌")

    status = "Enabled ✅"
    curr = status_db.find_one({"chat_id": message.chat.id})
    if curr and curr.get("status") == "disabled":
        status = "Disabled ❌"

    buttons = [[
        InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
        InlineKeyboardButton("Disable", callback_data="disable_chatbot")
    ]]
    await message.reply_text(f"**Chatbot Settings**\n\nStatus: {status}", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Access Denied!", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ Chatbot successfully **{action}d**!")
