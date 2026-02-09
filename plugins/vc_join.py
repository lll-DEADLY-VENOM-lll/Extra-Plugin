from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import ParticipantJoined, ParticipantLeft # Latest Version Names
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP # VIP-MUSIC ka pytgcalls instance

# Function to check if monitoring is enabled
def is_monitoring_enabled(chat_id):
    status = mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status["status"] == "on"

# Event: Jab koi VC Join kare (Latest Version Syntax)
@VIP.on_participant_joined()
async def vc_join_update(client, update: ParticipantJoined):
    chat_id = update.chat_id
    if is_monitoring_enabled(chat_id):
        user_id = update.user_id
        mention = f"[User](tg://user?id={user_id})"
        await app.send_message(chat_id, f"👤 {mention} ne VC join kiya.\n**User ID:** `{user_id}`")

# Event: Jab koi VC Leave kare (Latest Version Syntax)
@VIP.on_participant_left()
async def vc_leave_update(client, update: ParticipantLeft):
    chat_id = update.chat_id
    if is_monitoring_enabled(chat_id):
        user_id = update.user_id
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
    await message.reply("✅ VC monitoring start ho gayi hai.")

# Command to stop VC monitoring
@app.on_message(filters.command("checkvcoff") & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}}
    )
    await message.reply("❌ VC monitoring stop ho gayi hai.")
