from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update, CallParticipantUpdated
from pytgcalls.types.enums import ParticipantUpdateType
from VIPMUSIC.core.mongo import mongodb  # MongoDB connection
from VIPMUSIC import app
# Maan lete hain ki pytgcalls instance 'call' ya 'pytgcalls' ke naam se define hai
from VIPMUSIC import userbot # Ya jahan se bhi aapka pytgcalls instance aa raha hai

# Note: pytgcalls instance ko use karne ke liye aapko pata hona chahiye 
# ki aapne use kis naam se define kiya hai (e.g., pytgcalls = PyTgCalls(app))

# Function to check if monitoring is enabled for a group
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status["status"] == "on"

# Event to monitor VC join/leave
@pytgcalls.on_participant_updated()
async def vc_participant_update(client, update: CallParticipantUpdated):
    chat_id = update.chat_id
    
    # Database check (await lagana zaroori hai agar motor use kar rahe hain)
    if not await is_monitoring_enabled(chat_id):
        return

    user_id = update.participant._id # User ID nikaalne ke liye
    mention = f"[{user_id}](tg://user?id={user_id})"

    # Join Event
    if update.update_type == ParticipantUpdateType.JOINED:
        await app.send_message(chat_id, f"👤 {mention} ne VC join kiya.\nUser ID: `{user_id}`")

    # Leave Event
    elif update.update_type == ParticipantUpdateType.LEFT:
        await app.send_message(chat_id, f"🏃 {mention} ne VC leave kiya.\nUser ID: `{user_id}`")

# Command to start VC monitoring
@app.on_message(filters.command("checkvc") & filters.group)
async def vc_monitor_toggle(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /checkvc on | off")
    
    chat_id = message.chat.id
    state = message.command[1].lower()

    if state == "on":
        await mongodb.vc_monitoring.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "on"}},
            upsert=True
        )
        await message.reply("✅ VC monitoring started. Updates milna shuru ho jayenge.")
    elif state == "off":
        await mongodb.vc_monitoring.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "off"}},
            upsert=True
        )
        await message.reply("❌ VC monitoring stopped.")
    else:
        await message.reply("Invalid state! Use 'on' or 'off'.")
