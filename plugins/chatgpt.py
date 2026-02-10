import time
import requests
import io
import random
from urllib.parse import quote
from VIPMUSIC import app
from config import BANNED_USERS
from pyrogram.enums import ChatAction, ParseMode
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# API URLs
CHAT_API_URL = "https://chatgpt.apinepdev.workers.dev/?question="
IMAGE_API_URL = "https://image.pollinations.ai/prompt/"

# -----------------------------------------------------------------------
# 1. CHATGPT / AI TEXT COMMAND
# -----------------------------------------------------------------------

@app.on_message(filters.command(["chatgpt", "ai", "ask", "gpt", "solve"], prefixes=["+", ".", "/", "-", "", "$", "#", "&"]) & ~BANNED_USERS)
async def chat_gpt(bot, message):
    try:
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

        if len(message.command) < 2:
            return await message.reply_text(
                "**Usage:**\n\n`/chatgpt Where is the Taj Mahal?` \n`/ai Write a poem about love.`",
                parse_mode=ParseMode.MARKDOWN
            )

        question = message.text.split(' ', 1)[1]
        response = requests.get(f"{CHAT_API_URL}{question}")

        if response.status_code == 200:
            json_data = response.json()
            if "answer" in json_data:
                answer = json_data["answer"]

                # Aapka purana filtering logic
                unwanted_phrases = ["🔗 Join our community", "t.me/", "Answered by", "Join our Telegram"]
                for phrase in unwanted_phrases:
                    if phrase.lower() in answer.lower():
                        answer = answer.split(phrase)[0].strip()

                buttons = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✙ ʌᴅᴅ ϻє ɪη ʏσυʀ ɢʀσυᴘ ✙", url=f"https://t.me/{app.username}?startgroup=true")
                ]])

                return await message.reply_text(
                    f"**🤖 𝐀ɪ 𝐑ᴇsᴘᴏɴsᴇ :**\n\n{answer}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=buttons
                )
            else:
                return await message.reply_text("⚠️ No valid answer found in the API response.")
        else:
            return await message.reply_text(f"⚠️ API Error: Status code {response.status_code}")

    except Exception as e:
        return await message.reply_text(f"⚠️ **Error:** `{str(e)}`", parse_mode=ParseMode.MARKDOWN)


# -----------------------------------------------------------------------
# 2. PHOTO GENERATION / AI IMAGE COMMAND (Fixed Logo Problem)
# -----------------------------------------------------------------------

@app.on_message(filters.command(["generate", "draw", "photo", "imagine", "art"], prefixes=["+", ".", "/", "-", "", "$", "#", "&"]) & ~BANNED_USERS)
async def generate_image(bot, message):
    try:
        if len(message.command) < 2:
            return await message.reply_text(
                "**Kya banau?**\nExample: `/generate a beautiful girl in red dress` ",
                parse_mode=ParseMode.MARKDOWN
            )

        prompt = message.text.split(None, 1)[1]
        wait_msg = await message.reply_text("🎨 **Wait... I'm drawing your imagination...**")
        
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)

        # Prompt ko URL ke liye encode karna (Special characters handle karne ke liye)
        encoded_prompt = quote(prompt)
        
        # Har baar nayi image ke liye random seed
        seed = random.randint(1, 1000000)
        
        # Fixed Image URL (nologo=True se koi branding nahi aayegi)
        gen_url = f"{IMAGE_API_URL}{encoded_prompt}?seed={seed}&width=1024&height=1024&nologo=True"

        try:
            # Image download kar rahe hain taaki Telegram processor fail na ho
            response = requests.get(gen_url, timeout=60)
            if response.status_code == 200:
                photo = io.BytesIO(response.content)
                photo.name = "ai_image.jpg"

                await message.reply_photo(
                    photo=photo,
                    caption=f"**✨ 𝐏ʀᴏᴍᴘᴛ:** `{prompt}`\n**🤖 𝐆ᴇɴᴇʀᴀᴛᴇᴅ ʙʏ:** @{app.username}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✙ ʌᴅᴅ ϻє ɪη ʏσυʀ ɢʀσυᴘ ✙", url=f"https://t.me/{app.username}?startgroup=true")
                    ]])
                )
                await wait_msg.delete()
            else:
                await wait_msg.edit("❌ API is busy or returned an error. Try again.")
        
        except Exception as e:
            await wait_msg.edit(f"❌ **Failed to fetch image:** `{str(e)}`")

    except Exception as e:
        await message.reply_text(f"⚠️ **General Error:** `{str(e)}`", parse_mode=ParseMode.MARKDOWN)


# -----------------------------------------------------------------------
# MODULE INFO
# -----------------------------------------------------------------------

__MODULE__ = "Aɪ-Bᴏᴛ"
__HELP__ = """
**🤖 AI Commands:**

**1. ChatGPT:**
- `/ai [sawaal]` : AI se sawaal puchein.
- `/chatgpt [query]` : ChatGPT response.

**2. Photo Generate:**
- `/generate [prompt]` : AI photo banwayein.
- `/draw [prompt]` : Imagination ko image mein badlein.

**Example:**
`/generate a blue fire dragon in the dark sky`
"""
