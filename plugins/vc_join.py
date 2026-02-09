from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import Update
from pytgcalls.types.groups import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP

# Function to check if monitoring is enabled
def is_monitoring_enabled(chat_id):
    status = mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status["status"] == "on"

# FIX: VIP.userbot.on_update() use karein
@VIP.userbot.on_update()
async def vc_update_handler(client, update: Update):
    # Sirf join aur leave events ko handle karein
    if not isinstance(update, (JoinedGroupCallParticipant, LeftGroupCallParticipant)):
        return
    
    chat_id = update.chat_id
    if not is_monitoring_enabled(chat_id):
        return

    # Jab koi join kare
    if isinstance(update, JoinedGroupCallParticipant):
        user_id = update.participant.user_id
        mention = f"[User](tg://user?id={user_id})"
        try:
            await app.send_message(chat_id, f"👤 {mention} ne VC join kiya.\n**User ID:** `{user_id}`")
        except:
            pass

    # Jab koi leave kare
    elif isinstance(update, LeftGroupCallParticipant):
        user_id = update.participant.user_id
        mention = f"[User](tg://user?id={user_id})"
        try:
            await app.send_message(chat_id, f"🏃 {mention} ne VC leave kiya.\n**User ID:** `{user_id}`")
        except:
            pass

# Commands
@app.on_message(filters.command("checkvc on") & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply("✅ VC monitoring start ho gayi hai. Assistant ab join/leave track karega.")

@app.on_message(filters.command("checkvcoff") & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}}
    )
    await message.reply("❌ VC monitoring stop ho gayi hai.")
