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

# --- Text Cleaning Helper ---
def clean_input(text):
    # Punctuation hatana aur lower case karna
    return re.sub(r'[^\w\s]', '', text).lower().strip()

# --- Female Tone Logic ---
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

# --- Abuse Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine"]

def is_abusive(text):
    for word in ABUSIVE_WORDS:
        if re.search(rf"\b{word}\b", text.lower()):
            return True
    return False

# --- Better Reply Logic ---
async def get_reply(word: str):
    cleaned_word = clean_input(word)
    
    # 1. Sabse pehle exact match dhundo
    is_chat = list(chatai.find({"word": cleaned_word}))
    
    # 2. Agar exact nahi mila, toh regex se milta julta dhundo (Limited to 10 results)
    if not is_chat:
        is_chat = list(chatai.find({"word": {"$regex": cleaned_word, "$options": "i"}}).limit(10))
    
    # Yahan se RANDOM SAMPLE wala kachra logic hata diya gaya hai.
    
    if is_chat:
        return random.choice(is_chat)
    return None

# --- Chatbot Response Logic ---
@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    
    # Check if chatbot is enabled
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    if message.text and any(message.text.startswith(p) for p in ["/", "!", ".", "?", "@"]):
        return

    if message.text and is_abusive(message.text):
        await message.reply_text("Aap bahut gande ho, tameez se baat karo! 😡")
        return

    input_text = message.text if message.text else ""
    # Keywords for triggering
    keywords = ["hi", "hello", "kaise ho", "bot", nexichat.name.lower()]
    
    is_keyword = any(re.search(rf"\b{word}\b", input_text.lower()) for word in keywords)
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await client.get_me()).id
    is_private = message.chat.type.value == "private"

    if is_keyword or is_reply_to_me or is_private:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        
        reply_data = await get_reply(input_text)
        
        if reply_data:
            response_text = reply_data["text"]
            if reply_data.get("check") != "sticker" and reply_data.get("check") != "photo":
                response_text = make_female_tone(response_text)

            # Translation
            chat_lang = lang_db.find_one({"chat_id": chat_id})
            chat_lang = chat_lang["language"] if chat_lang and "language" in chat_lang else None
            
            if chat_lang and chat_lang not in ["en", "nolang"]:
                try:
                    response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
                except:
                    pass

            if reply_data.get("check") == "sticker":
                await message.reply_sticker(reply_data["text"])
            elif reply_data.get("check") == "photo":
                await message.reply_photo(reply_data["text"])
            else:
                await message.reply_text(response_text)
        else:
            # Agar bot ko kuch nahi pata, toh ek default sweet reply
            default_replies = [
                "Hmm... main abhi seekh rahi hoon, thoda dhang se batao? 🥺",
                "Aapki baatein mere sar ke upar se gayi, fir se bolo? ✨",
                "Mujhe iska jawab nahi pata, par aap bahut pyaare ho! 😊"
            ]
            await message.reply_text(random.choice(default_replies))

    # --- Learning Logic ---
    if message.reply_to_message and not is_abusive(message.text):
        if message.reply_to_message.text:
            await save_reply(message.reply_to_message.text, message)

async def save_reply(original_text: str, reply_message: Message):
    cleaned_original = clean_input(original_text)
    content = reply_message.text or (reply_message.sticker.file_id if reply_message.sticker else None)
    
    if not content or len(cleaned_original) < 2:
        return

    check_type = "sticker" if reply_message.sticker else "none"
    
    # Check duplicate
    exists = chatai.find_one({"word": cleaned_original, "text": content})
    if not exists:
        chatai.insert_one({
            "word": cleaned_original,
            "text": content,
            "check": check_type
        })
