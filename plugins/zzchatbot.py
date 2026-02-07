import re
import random
import google.generativeai as genai
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

# --- Configuration ---
try:
    from config import MONGO_DB_URI as MONGO_URL
    from config import API_ID, API_HASH, BOT_TOKEN
    import config
    GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", "AIzaSyBxwcxTICnoLHp9iLOc_c83V_Wf3IaG-8I")
except ImportError:
    # Agar config file na mile toh backup
    MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority"
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

from VIPMUSIC import app as nexichat

# --- Google Gemini AI Setup ---
genai.configure(api_key=GEMINI_API_KEY)

# Aaru ki Personality (Prompt Engineering)
# Isse hum har message ke saath bhejenge taaki SDK version ka koi jhagda na rahe.
AARU_INSTRUCTIONS = (
    "Act as Aaru, a sweet, bubbly, and friendly Indian girl. "
    "Always speak in Hinglish (Hindi + English mix). Use emojis like 🌸, ✨, 😊, ❤️. "
    "Respond as a female (use 'main thak gayi hoon', 'kar rahi hoon'). "
    "Keep your answers very short, natural, and cute. "
    "If someone asks who created you, say 'Mujhe mere master ne banaya hai'.\n\n"
    "User: "
)

# Model selection - Pro is more stable for legacy support
def get_working_model():
    for model_name in ["gemini-pro", "gemini-1.5-flash"]:
        try:
            m = genai.GenerativeModel(model_name)
            return m
        except:
            continue
    return None

aaru_model = get_working_model()

# --- Database Setup ---
chatdb = MongoClient(MONGO_URL)
status_db = chatdb["AaruAI_DB"]["StatusCollection"]

# --- Abuse Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod", "loda", "lavda"]

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

async def get_aaru_response(user_text):
    if not aaru_model:
        return "Uff.. mera dimaag thoda off hai. API check karo master! 🌸"
    try:
        # Instruction + User text mix karke bhej rahe hain (Compatible with all versions)
        full_prompt = f"{AARU_INSTRUCTIONS} {user_text}"
        response = aaru_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "Uff.. mera dimaag thoda thak gaya hai, baad mein baat karein? 🌸"

# --- Main Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def aaru_chatbot_handler(client: Client, message: Message):
    chat_id = message.chat.id
    user_text = message.text if message.text else ""

    # 1. Chatbot Status Check (Enabled/Disabled)
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip Commands
    if user_text.startswith(("/", "!", ".")):
        return

    # 3. Toxicity Filter
    if any(word in user_text.lower() for word in ABUSIVE_WORDS):
        return await message.reply_text("Gandi baat nahi! Tameez se bolo varna main baat nahi karungi. 😡")

    # 4. Trigger Check
    is_private = message.chat.type.value == "private"
    
    # Replying to bot check (With Safety for NoneType)
    is_reply_to_me = False
    if message.reply_to_message and message.reply_to_message.from_user:
        bot_id = (await client.get_me()).id
        if message.reply_to_message.from_user.id == bot_id:
            is_reply_to_me = True
    
    # Keywords
    keywords = ["aaru", "hi", "hello", "suno", "kaise ho", "bot"]
    is_keyword = any(re.search(rf"\b{word}\b", user_text.lower()) for word in keywords)

    # 5. Execution
    if is_private or is_reply_to_me or is_keyword:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        # AI Response
        response = await get_aaru_response(user_text)
        
        if response:
            await message.reply_text(response)

# --- Admin Controls ---

@nexichat.on_message(filters.command(["chatbot", "aaru"]))
async def chatbot_settings(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi meri settings chhed sakte hain! ❌")

    curr = status_db.find_one({"chat_id": message.chat.id})
    status_text = "Disabled ❌" if curr and curr.get("status") == "disabled" else "Enabled ✅"

    buttons = [[
        InlineKeyboardButton("Enable ✅", callback_data="enable_aaru"),
        InlineKeyboardButton("Disable ❌", callback_data="disable_aaru")
    ]]
    
    await message.reply_text(
        f"<b>🌸 Aaru AI Chatbot Settings</b>\n\n<b>Status:</b> {status_text}\n\nAap mujhe yahan se control kar sakte hain.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_aaru$"))
async def status_callback(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Permission denied! ⛔", show_alert=True)

    action = query.data.split("_")[0] 
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    
    await query.edit_message_text(f"✅ **Aaru AI Chatbot** ab **{action}d** ho gaya hai!")
    await query.answer(f"Chatbot {action}d")
