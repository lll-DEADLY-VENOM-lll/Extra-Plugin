import random
import re
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from deep_translator import GoogleTranslator 
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

chatdb = MongoClient(MONGO_URL)
worddb = MongoClient(WORD_MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
chatai = worddb["Word"]["WordDb"] 
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# --- Constants & Config ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod"]
KEYWORDS = ["hi", "hello", "hii", "hey", "namaste", "kaise ho", "bot", "zoya", "sweety"] # 'zoya' example name

# --- Female Tone Logic (Enhanced) ---
def make_female_tone(text):
    replacements = {
        r"\braha hoon\b": "rahi hoon",
        r"\braha tha\b": "rahi thi",
        r"\braha hai\b": "rahi hai",
        r"\bgaya tha\b": "gayi thi",
        r"\bgaya\b": "gayi",
        r"\btha\b": "thi",
        r"\bkhata hoon\b": "khati hoon",
        r"\bkarunga\b": "karungi",
        r"\baaunga\b": "aaungi",
        r"\bdekhunga\b": "dekhungi",
        r"\bbhai\b": "behen 🌸",
        r"\bbhaiya\b": "didi",
        r"\babbe\b": "aree",
        r"\bpagal\b": "pagli",
        r"\bmere\b": "meri",
        r"\bbeta\b": "bacche"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Adding a soft touch
    if not any(emoji in text for emoji in ["❤️", "✨", "😊", "🙈"]):
        text += " ✨"
    return text

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id < 0: # Group check
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    return True # Private chat mein user hi admin hai

def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else "hi"

async def get_reply(word: str):
    is_chat = list(chatai.find({"word": word.lower()}))
    if not is_chat:
        # Fuzzy search ki jagah random sample fallback
        is_chat = list(chatai.aggregate([{"$sample": {"size": 1}}]))
    
    return random.choice(is_chat) if is_chat else None

# --- Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=1)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    user_text = message.text.lower() if message.text else ""

    # 1. Status Check
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Command/Link Filter
    if user_text.startswith(("/", "!", ".")) or "http" in user_text:
        return

    # 3. Abuse Filter
    if any(word in user_text for word in ABUSIVE_WORDS):
        await message.reply_text("Aap bahut gande ho, tameez se baat karo! 😡")
        return

    # 4. Trigger Conditions
    is_reply_to_me = (message.reply_to_message and message.reply_to_message.from_user.id == (await client.get_me()).id)
    is_keyword = any(re.search(rf"\b{word}\b", user_text) for word in KEYWORDS)
    is_private = message.chat.type.value == "private"

    if is_keyword or is_reply_to_me or is_private:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        reply_data = await get_reply(user_text)
        
        if reply_data:
            response_text = reply_data["text"]
            
            # Tone conversion
            if reply_data.get("check") != "sticker" and reply_data.get("check") != "photo":
                response_text = make_female_tone(response_text)

            # Translation Logic
            chat_lang = get_chat_language(chat_id)
            if chat_lang not in ["hi", "en", "nolang"]:
                try:
                    response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
                except:
                    pass

            # Final Reply
            if reply_data.get("check") == "sticker":
                await message.reply_sticker(response_text)
            elif reply_data.get("check") == "photo":
                await message.reply_photo(response_text)
            else:
                await message.reply_text(response_text)
        else:
            await message.reply_text("Umm... main samajh nahi paayi, kya bola aapne? 🥺")

    # --- Learning Logic ---
    if message.reply_to_message and not any(word in user_text for word in ABUSIVE_WORDS):
        # Don't learn very short or useless replies
        if message.text and len(message.text) > 2:
            await save_reply(message.reply_to_message, message)

async def save_reply(original_message: Message, reply_message: Message):
    if not original_message.text or not (reply_message.text or reply_message.sticker):
        return
    
    content = reply_message.text or reply_message.sticker.file_id
    check_type = "sticker" if reply_message.sticker else "none"
    
    # Check if exists to avoid duplicates
    trigger = original_message.text.lower()
    if not chatai.find_one({"word": trigger, "text": content}):
        chatai.insert_one({
            "word": trigger,
            "text": content,
            "check": check_type
        })

# --- Commands ---

@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    # Admin check
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi chatbot settings badal sakte hain! ❌")

    status = "Enabled ✅"
    current_status = status_db.find_one({"chat_id": message.chat.id})
    if current_status and current_status.get("status") == "disabled":
        status = "Disabled ❌"

    buttons = [
        [
            InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
            InlineKeyboardButton("Disable", callback_data="disable_chatbot")
        ],
        [InlineKeyboardButton("Close", callback_data="close_chat")]
    ]
    
    await message.reply_text(
        f"<b>🤖 Chatbot Settings</b>\n\n<b>Current Status:</b> {status}\n<b>Chat ID:</b> `{message.chat.id}`\n\nSelect an option below:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Aapke paas permission nahi hai! ⛔", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    
    await query.answer(f"Chatbot {action}d successfully!", show_alert=True)
    await query.edit_message_text(f"✅ Chatbot status updated to: **{action.capitalize()}d**")

@nexichat.on_callback_query(filters.regex("close_chat"))
async def close_cb(client, query):
    await query.message.delete()
