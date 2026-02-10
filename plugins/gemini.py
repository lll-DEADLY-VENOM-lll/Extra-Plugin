import httpx
import urllib.parse
from pyrogram import filters
from pyrogram.enums import ChatAction
from VIPMUSIC import app

# --- Unofficial API Function ---
async def get_gemini_response(prompt):
    try:
        # Prompt ko URL safe banane ke liye encode karna zaroori hai
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Unofficial Public API (No Key Required)
        url = f"https://api.sandipapi.workers.dev/gemini?query={encoded_prompt}"
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # Sandip API usually returns the answer in 'answer' key
                return data.get("answer")
            return None
    except Exception as e:
        print(f"API Error: {e}")
        return None

@app.on_message(filters.command(["gemini"]))
async def gemini_handler(client, message):
    if len(message.command) > 1:
        user_input = message.text.split(None, 1)[1]
    elif message.reply_to_message and message.reply_to_message.text:
        user_input = message.reply_to_message.text
    else:
        return await message.reply_text("ᴇxᴀᴍᴘʟᴇ :- `/gemini who is lord ram`")

    await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    result = await get_gemini_response(user_input)
    
    if result:
        await message.reply_text(result, quote=True)
    else:
        # Fallback agar pehla API fail ho jaye
        await message.reply_text("sᴏʀʀʏ! Unofficial API is currently busy. Try again later.")

@app.on_message(filters.group & ~filters.bot, group=50)
async def chatbot_handler(client, message):
    if not message.text or message.text.startswith(("/", "!", ".")):
        return

    # Check if bot is replied to
    bot_obj = await client.get_me()
    if message.reply_to_message and message.reply_to_message.from_user.id == bot_obj.id:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Chhota prompt for girl persona
        persona_query = f"Reply as a cute chatty girl in one short line to: {message.text}"
        
        result = await get_gemini_response(persona_query)
        if result:
            await message.reply_text(result, quote=True)

__MODULE__ = "Gᴇᴍɪɴɪ"
__HELP__ = "/gemini [ǫᴜᴇʀʏ] - ᴀsᴋ ʏᴏᴜʀ ǫᴜᴇsᴛɪᴏɴ ᴡɪᴛʜ ɢᴇᴍɪɴɪ ᴀɪ"
