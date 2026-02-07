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
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

chatdb = MongoClient(MONGO_URL)
worddb = MongoClient(WORD_MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
chatai = worddb["Word"]["WordDb"]
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# --- Configuration ---
# Kitne percent messages par reply kare? (0.6 = 60% chance)
# Agar aap chahte hain 100% reply kare, toh ise 1.0 kar dein.
CHAT_CHANCE = 0.6 

def clean_input(text):
    return re.sub(r'[^\w\s]', '', text).lower().strip()

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
        r"\bbhai\b": "behen",
        r"\bbhaiya\b": "didi",
        r"\babbe\b": "aree",
        r"\bpagal\b": "pagli"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

async def get_reply(word: str):
    cleaned_word = clean_input(word)
    # Sabse pehle poore sentence ka match dhundo
    is_chat = list(chatai.find({"word": cleaned_word}))
    
    # Agar pura sentence nahi milta, toh keywords dhundo
    if not is_chat:
        words = cleaned_word.split()
        if words:
            # Sentence ke kisi bhi ek bade word se reply dhundne ki koshish
            random_word = max(words, key=len) 
            is_chat = list(chatai.find({"word": {"$regex": random_word, "$options": "i"}}).limit(5))
    
    if is_chat:
        return random.choice(is_chat)
    return None

# --- Main Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=1)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    
    # 1. Check if disabled
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # 2. Skip commands
    if message.text and any(message.text.startswith(p) for p in ["/", "!", ".", "?", "@"]):
        return

    # 3. Handle Private & Groups
    is_private = message.chat.type.value == "private"
    
    # Random probability check for groups (taki bot spammer na lage)
    # Private mein 100% reply karega, group mein CHAT_CHANCE ke hisaab se
    if not is_private and random.random() > CHAT_CHANCE:
        # Lekin agar kisi ne bot ko reply kiya hai, toh 100% reply dena chahiye
        is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await client.get_me()).id
        if not is_reply_to_me:
            return

    # 4. Process Response
    input_text = message.text if message.text else ""
    await client.send_chat_action(chat_id, ChatAction.TYPING)
    
    reply_data = await get_reply(input_text)
    
    if reply_data:
        response_text = reply_data["text"]
        
        # Apply female tone to text
        if reply_data.get("check") not in ["sticker", "photo"]:
            response_text = make_female_tone(response_text)

        # Translation Logic
        chat_lang = lang_db.find_one({"chat_id": chat_id})
        chat_lang = chat_lang["language"] if chat_lang and "language" in chat_lang else None
        if chat_lang and chat_lang not in ["en", "nolang"]:
            try:
                response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
            except: pass

        # Send Reply
        if reply_data.get("check") == "sticker":
            await message.reply_sticker(reply_data["text"])
        elif reply_data.get("check") == "photo":
            await message.reply_photo(reply_data["text"])
        else:
            await message.reply_text(response_text)
    else:
        # Agar bot ke paas koi match nahi hai, toh random cute response (sirf private ya tag karne pe)
        if is_private or (message.reply_to_message and message.reply_to_message.from_user.id == (await client.get_me()).id):
            defaults = ["Hmm..", "Achha?", "Oho..", "Main samajh rahi hoon 😊", "Hehe, okay!"]
            await message.reply_text(random.choice(defaults))

    # --- Continuous Learning ---
    # Har message se seekho (agar wo reply hai toh)
    if message.reply_to_message and message.text:
        await save_reply(message.reply_to_message.text, message)

async def save_reply(original_text: str, reply_message: Message):
    # Gali filter
    ABUSIVE = ["saala", "bc", "mc", "chutiya", "randi"]
    if any(x in reply_message.text.lower() for x in ABUSIVE) if reply_message.text else False:
        return

    cleaned_original = clean_input(original_text)
    content = reply_message.text or (reply_message.sticker.file_id if reply_message.sticker else None)
    
    if not content or len(cleaned_original) < 2:
        return

    check_type = "sticker" if reply_message.sticker else "none"
    
    if not chatai.find_one({"word": cleaned_original, "text": content}):
        chatai.insert_one({"word": cleaned_original, "text": content, "check": check_type})

# --- Toggle Command ---
@nexichat.on_message(filters.command("chatbot") & filters.group)
async def chat_toggle(client: Client, message: Message):
    # ... (Same as your button logic)
    pass
