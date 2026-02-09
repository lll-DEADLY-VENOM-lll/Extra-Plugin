from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP

# MongoDB check function
def is_monitoring_enabled(chat_id):
    status = mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status["status"] == "on"

# FIX: Version 1.2.9 mein 'on_participants_change' use hota hai
@VIP.one.on_participants_change()
async def vc_participants_handler(client, update):
    chat_id = update.chat_id
    
    # Check if monitoring is ON for this chat
    if not is_monitoring_enabled(chat_id):
        return

    # User Join Check
    if isinstance(update, JoinedGroupCallParticipant):
        user_id = update.participant.user_id
        mention = f"[User](tg://user?id={user_id})"
        try:
            await app.send_message(chat_id, f"👤 {mention} ne VC join kiya.\n**User ID:** `{user_id}`")
        except:
            pass

    # User Leave Check
    elif isinstance(update, LeftGroupCallParticipant):
        user_id = update.participant.user_id
        mention = f"[User](tg://user?id={user_id})"
        try:
            await app.send_message(chat_id, f"🏃 {mention} ne VC leave kiya.\n**User ID:** `{user_id}`")
        except:
            pass

# Commands to turn ON/OFF
@app.on_message(filters.command("checkvc on") & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply("✅ **VC Monitoring ON:** Ab Assistant join/leave track karega.")

@app.on_message(filters.command("checkvcoff") & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}}
    )
    await message.reply("❌ **VC Monitoring OFF.**")
