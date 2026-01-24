import random
import re
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from deep_translator import GoogleTranslator 
from config import MONGO_DB_URI as MONGO_URL
import config
from VIPMUSIC import app as nexichat

# --- Database Setup ---
# Is database se bot dushron ki baatein seekhega aur reply karega
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

chatdb = MongoClient(MONGO_URL)
worddb = MongoClient(WORD_MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
chatai = worddb["Word"]["WordDb"] # Yahan se learning data aayega
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# --- Female Tone Logic ---
def make_female_tone(text):
    """Hindi/Urdu masculine words ko feminine mein convert karne ke liye"""
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
        r"\bbhai\b": "behen",
        r"\bbhaiya\b": "didi",
        r"\babbe\b": "aree",
        r"\bpagal\b": "pagli"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# --- Abuse Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine"]

def is_abusive(text):
    for word in ABUSIVE_WORDS:
        if re.search(rf"\b{word}\b", text.lower()):
            return True
    return False

# --- Helper Functions ---
def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else None

async def get_reply(word: str):
    # Pehle exact match dhundo database mein
    is_chat = list(chatai.find({"word": word.lower()}))
    if not is_chat:
        # Agar word nahi milta to random koi bhi reply uthao (Learning from others)
        is_chat = list(chatai.aggregate([{"$sample": {"size": 1}}]))
    
    if is_chat:
        return random.choice(is_chat)
    return None

# --- Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    
    # Check if chatbot is enabled
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # Skip commands
    if message.text and any(message.text.startswith(p) for p in ["/", "!", ".", "?", "@"]):
        return

    # Abuse filter
    if message.text and is_abusive(message.text):
        await message.reply_text("Aap bahut gande ho, tameez se baat karo! 😡")
        return

    # Response Trigger Condition
    # 1. Private chat ho
    # 2. Group mein bot ko reply kiya ho
    # 3. Group mein koi "hi", "hello", "kaise ho" jaise keywords likhe
    input_text = message.text.lower() if message.text else ""
    keywords = ["hi", "hello", "hii", "hey", "namaste", "kaise ho", "bot", nexichat.name.lower()]
    
    is_keyword = any(re.search(rf"\b{word}\b", input_text) for word in keywords)
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await client.get_me()).id
    is_private = message.chat.type.value == "private"

    if is_keyword or is_reply_to_me or is_private:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        reply_data = await get_reply(input_text)
        
        if reply_data:
            response_text = reply_data["text"]
            
            # Female tone apply karo
            if reply_data.get("check") == "none" or not reply_data.get("check"):
                response_text = make_female_tone(response_text)

            # Translation Logic
            chat_lang = get_chat_language(chat_id)
            if chat_lang and chat_lang != "en" and chat_lang != "nolang":
                try:
                    response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
                except:
                    pass

            # Final Reply
            if reply_data.get("check") == "sticker":
                await message.reply_sticker(reply_data["text"])
            elif reply_data.get("check") == "photo":
                await message.reply_photo(reply_data["text"])
            else:
                # Add a female touch to empty/unknown responses
                if not response_text or response_text == "":
                    response_text = "Main abhi thoda busy hoon ji, baad mein baat karein? ✨"
                await message.reply_text(response_text)
        else:
            await message.reply_text("Umm... main samajh nahi paayi, kya bola aapne? 🥺")

    # --- Learning Logic ---
    # Bot dushron ki baaton se seekhta rahega (Agar gali nahi hai to)
    if message.reply_to_message and not is_abusive(message.text):
        await save_reply(message.reply_to_message, message)

async def save_reply(original_message: Message, reply_message: Message):
    if not original_message.text:
        return
    
    content = reply_message.text or (reply_message.sticker.file_id if reply_message.sticker else None)
    if not content:
        return

    check_type = "sticker" if reply_message.sticker else "none"
    
    # Check if exists
    is_chat = chatai.find_one({"word": original_message.text.lower(), "text": content})
    if not is_chat:
        chatai.insert_one({
            "word": original_message.text.lower(),
            "text": content,
            "check": check_type
        })

# --- Commands ---

@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    buttons = [[
        InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
        InlineKeyboardButton("Disable", callback_data="disable_chatbot")
    ]]
    await message.reply_text(f"**Chatbot Control for {message.chat.title}**", reply_markup=InlineKeyboardMarkup(buttons))

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.answer(f"Chatbot {action}d!", show_alert=True)
    await query.edit_message_text(f"Chatbot has been **{action}d** successfully.")
