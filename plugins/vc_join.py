from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types.update import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb  # MongoDB connection
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP # VIP-MUSIC mein pytgcalls instance 'VIP' ke naam se hota hai

# Function to check if monitoring is enabled for a group
def is_monitoring_enabled(chat_id):
    status = mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status["status"] == "on"

# Event to monitor VC join/leave (Version 1.2.9 Syntax)
@VIP.on_update()
async def vc_participant_update(client, update):
    # Chat ID nikalne ka tarika 1.2.9 mein
    chat_id = update.chat_id
    
    if not is_monitoring_enabled(chat_id):
        return

    # User Join Check
    if isinstance(update, JoinedGroupCallParticipant):
        user_id = update.participant.user_id
        mention = f"[User](tg://user?id={user_id})"
        await app.send_message(chat_id, f"👤 {mention} ne VC join kiya.\n**User ID:** `{user_id}`")

    # User Leave Check
    elif isinstance(update, LeftGroupCallParticipant):
        user_id = update.participant.user_id
        mention = f"[User](tg://user?id={user_id})"
        await app.send_message(chat_id, f"🏃 {mention} ne VC leave kiya.\n**User ID:** `{user_id}`")

# Command to start VC monitoring
@app.on_message(filters.command("checkvc on") & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply("✅ VC monitoring start kar di gayi hai.")

# Command to stop VC monitoring
@app.on_message(filters.command("checkvcoff") & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}}
    )
    await message.reply("❌ VC monitoring stop kar di gayi hai.")
