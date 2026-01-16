import requests
from pyrogram import filters
from pyrogram.enums import ChatAction
from VIPMUSIC import app
from config import BANNED_USERS

# Ek common function AI response fetch karne ke liye
def get_ai_response(prompt):
    try:
        # Hum yahan ek free public API use kar rahe hain
        url = f"https://chnm-ai-api.vercel.app/chat?q={prompt}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("reply", "Sorry, response nahi mil paya.")
        else:
            return "API me error hai, baad me koshish karein."
    except Exception as e:
        return f"Error: {e}"

@app.on_message(filters.command(["detect", "aidetect", "asklang"]) & ~BANNED_USERS)
async def chatgpt_chat_lang(bot, message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text("**Provide any text after command or reply to any message**")
        return

    if message.reply_to_message and message.reply_to_message.text:
        user_text = message.reply_to_message.text
    else:
        user_text = " ".join(message.command[1:])

    user_input = f"""
    Sentences :- {user_text}
    Mujhe is sentence ka language name aur code batao, aur usi language me ek chhota sa reply do.
    Format:
    Lang :- 
    Code :- 
    Reply :- 
    """

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    results = get_ai_response(user_input)
    await message.reply_text(results)


@app.on_message(filters.command(["chatgpt", "ai", "ask"]) & ~BANNED_USERS)
async def chatgpt_chat(bot, message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(
            "Example:\n\n`/ai write simple website code using html css, js?`"
        )
        return

    if message.reply_to_message and message.reply_to_message.text:
        user_input = message.reply_to_message.text
    else:
        user_input = " ".join(message.command[1:])

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    results = get_ai_response(user_input)
    await message.reply_text(results)

__MODULE__ = "CʜᴀᴛGᴘᴛ"
__HELP__ = """
/ai [ǫᴜᴇʀʏ] - ᴀsᴋ ʏᴏᴜʀ ǫᴜᴇsᴛɪᴏɴ ᴡɪᴛʜ ᴀɪ
/detect [ᴛᴇxᴛ] - ᴅᴇᴛᴇᴄᴛ ʟᴀɴɢᴜᴀɢᴇ ᴀɴᴅ ɢᴇᴛ ʀᴇᴘʟʏ
"""
