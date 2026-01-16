import requests
from pyrogram import filters
from pyrogram.enums import ChatAction
from VIPMUSIC import app

# Gemini API function - Bina kisi library dependency ke
def get_gemini_response(prompt):
    try:
        # Hum yahan ek stable free API use kar rahe hain
        url = f"https://chnm-ai-api.vercel.app/gemini?q={prompt}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Check if response is not None and has the 'reply' key
            return data.get("reply")
        return None
    except Exception:
        return None

@app.on_message(filters.command(["gemini"]))
async def gemini_handler(client, message):
    await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # User input extraction
    if len(message.command) > 1:
        user_input = " ".join(message.command[1:])
    elif message.reply_to_message and message.reply_to_message.text:
        user_input = message.reply_to_message.text
    else:
        return await message.reply_text("ᴇxᴀᴍᴘʟᴇ :- `/gemini who is lord ram`")

    # API Call
    result = get_gemini_response(user_input)
    
    if result:
        await message.reply_text(result, quote=True)
    else:
        await message.reply_text("sᴏʀʀʏ sɪʀ! ᴀᴘɪ ɪs ɴᴏᴛ ʀᴇsᴘᴏɴᴅɪɴɢ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.")

@app.on_message(filters.group, group=50)
async def chatbot_handler(client, message):
    # Sirf tab reply kare jab bot ko reply kiya gaya ho
    if not message.text or any(message.text.startswith(prefix) for prefix in ["!", "/", ".", "?", "@", "#"]):
        return

    if message.reply_to_message and message.reply_to_message.from_user.id == (await client.get_me()).id:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        user_input = f"""
            User says: ({message.text})
            Task: Tum ek ladki ho, ekdam chatty aur mazedar reply do. 
            Rules: 
            1. Reply bahut chhota hona chahiye (max 1 line).
            2. Same language use karo jisme user ne pucha hai.
            3. Ladki jaisa behave karo (masti bhara).
            4. Agar sirf emoji hai toh emoji me reply do.
            Sirf reply likho, kuch extra nahi.
        """
        
        result = get_gemini_response(user_input)
        
        if result:
            await message.reply_text(result, quote=True)
        else:
            # Agar API fail ho jaye toh silent rahein ya chhota error den
            pass

__MODULE__ = "Gᴇᴍɪɴɪ"
__HELP__ = "/gemini [ǫᴜᴇʀʏ] - ᴀsᴋ ʏᴏᴜʀ ǫᴜᴇsᴛɪᴏɴ ᴡɪᴛʜ ɢᴇᴍɪɴɪ ᴀɪ"
