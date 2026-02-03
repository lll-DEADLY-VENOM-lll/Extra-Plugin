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
# Pehla DB: Chat settings ke liye
# Dusra DB: Words aur Replies seekhne ke liye
WORD_MONGO_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

chatdb = MongoClient(MONGO_URL)
worddb = MongoClient(WORD_MONGO_URL)
status_db = chatdb["ChatBotStatusDb"]["StatusCollection"]
chatai = worddb["Word"]["WordDb"] 
lang_db = chatdb["ChatLangDb"]["LangCollection"]

# --- Female Tone Logic (Ladki ki tarah bolne ke liye) ---
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
        r"\bpagal\b": "pagli",
        r"\bhoon\b": "hoon ji ✨"
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# --- Abuse Filter ---
ABUSIVE_WORDS = ["saala", "bc", "mc", "chutiya", "randi", "bhadwa", "kamine", "gaand", "madarchod"]

# --- Fallback Replies (Jab bot ke paas jawab na ho) ---
FALLBACK_REPLIES = [
    "Hmm.. ye toh maine pehle nahi suna! ✨",
    "Achha? Aur batao, main seekh rahi hoon. 😊",
    "Umm.. thoda aur samjhao na? 🌸",
    "Hehe, interesting! ✨",
    "Baat toh sahi hai aapki. ✨",
    "Hmm.. aur kya chal raha hai?",
    "Aap bohot achhi baatein karte ho! 😊"
]

# --- Helper Functions ---
async def is_admin(client, chat_id, user_id):
    if chat_id > 0: return True 
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

def get_chat_language(chat_id):
    chat_lang = lang_db.find_one({"chat_id": chat_id})
    return chat_lang["language"] if chat_lang and "language" in chat_lang else "hi"

async def get_reply(word: str):
    # Database mein reply dhundna
    is_chat = list(chatai.find({"word": word}))
    if is_chat:
        return random.choice(is_chat)
    return None

# --- Main Chatbot Logic ---

@nexichat.on_message((filters.text | filters.sticker) & ~filters.bot, group=2)
async def chatbot_response(client: Client, message: Message):
    chat_id = message.chat.id
    bot_id = (await client.get_me()).id
    
    # Input handle karna (Text ho ya Sticker)
    user_input = message.text.lower() if message.text else (message.sticker.file_id if message.sticker else None)
    
    if not user_input: return

    # 1. Learning Logic (Automatic Seekhna)
    # Agar koi ek dusre ko reply de raha hai toh unki baatein save karo
    if message.reply_to_message and not any(word in (message.text or "").lower() for word in ABUSIVE_WORDS):
        await save_reply(message.reply_to_message, message)

    # 2. Check Chatbot Status (Enable/Disable)
    chat_status = status_db.find_one({"chat_id": chat_id})
    if chat_status and chat_status.get("status") == "disabled":
        return

    # Commands ko skip karein
    if message.text and message.text.startswith(("/", "!", ".")):
        return

    # 3. Trigger Logic (Bot kab bolegi)
    is_private = message.chat.type.value == "private"
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == bot_id
    is_mentioned = message.text and f"@{client.me.username}" in message.text
    
    # Keywords jinpar bot active ho jaye
    keywords = ["zoya", "bot", "zoyubot", "sun", "hey", "hello"]
    is_keyword = message.text and any(re.search(rf"\b{word}\b", user_input) for word in keywords)

    # Reaction Logic
    if is_private or is_reply_to_me or is_mentioned or is_keyword:
        
        # Abuse filter
        if message.text and any(word in user_input for word in ABUSIVE_WORDS):
            return await message.reply_text("Gandi baat nahi karte! Tameez se bolo. 😡")

        # Typing action
        await client.send_chat_action(chat_id, ChatAction.TYPING if message.text else ChatAction.CHOOSE_STICKER)
        
        reply_data = await get_reply(user_input)
        
        if reply_data:
            response_text = reply_data["text"]
            check_type = reply_data.get("check")

            if check_type == "sticker":
                await message.reply_sticker(response_text)
            else:
                # Text processing
                response_text = make_female_tone(response_text)
                chat_lang = get_chat_language(chat_id)
                if chat_lang not in ["hi", "en", "nolang"]:
                    try:
                        response_text = GoogleTranslator(source='auto', target=chat_lang).translate(response_text)
                    except: pass
                await message.reply_text(response_text)
        else:
            # Agar bot ko jawab nahi pata toh fallback reply do
            if not message.sticker: # Stickers par fallback nahi dete
                fallback = random.choice(FALLBACK_REPLIES)
                await message.reply_text(make_female_tone(fallback))

async def save_reply(original_message: Message, reply_message: Message):
    # Trigger (Jis baat ka reply diya gaya)
    trigger = original_message.text.lower() if original_message.text else (original_message.sticker.file_id if original_message.sticker else None)
    
    # Content (Jo naya reply diya gaya)
    content = reply_message.text if reply_message.text else (reply_message.sticker.file_id if reply_message.sticker else None)
    
    if not trigger or not content: return

    check_type = "sticker" if reply_message.sticker else "none"
    
    # Check duplicate and save
    if not chatai.find_one({"word": trigger, "text": content}):
        chatai.insert_one({
            "word": trigger, 
            "text": content, 
            "check": check_type
        })

# --- Admin Commands ---

@nexichat.on_message(filters.command("chatbot"))
async def chat_toggle(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("Sirf admins hi ye kar sakte hain! ❌")

    status = "Enabled ✅"
    curr = status_db.find_one({"chat_id": message.chat.id})
    if curr and curr.get("status") == "disabled":
        status = "Disabled ❌"

    buttons = [[
        InlineKeyboardButton("Enable", callback_data="enable_chatbot"),
        InlineKeyboardButton("Disable", callback_data="disable_chatbot")
    ]]
    await message.reply_text(
        f"<b>Chatbot Settings for {message.chat.title if message.chat.title else 'Private Chat'}</b>\n\nStatus: {status}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@nexichat.on_callback_query(filters.regex(r"^(enable|disable)_chatbot$"))
async def cb_handler(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.message.chat.id, query.from_user.id):
        return await query.answer("Access Denied! ⛔", show_alert=True)

    action = query.data.split("_")[0]
    status_db.update_one({"chat_id": query.message.chat.id}, {"$set": {"status": f"{action}d"}}, upsert=True)
    await query.edit_message_text(f"✅ Chatbot has been **{action}d** successfully!")
