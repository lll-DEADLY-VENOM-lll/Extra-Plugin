from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update, CallParticipantUpdated  # Naya tarika
from pytgcalls.types.enums import ParticipantStatus          # Status check karne ke liye
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app

# Pytgcalls ko initialize kiya (Agar aapke core mein pehle se hai toh use hi use karein)
pytgcalls = PyTgCalls(app)

# 1. Database check karne ka function
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# 2. Join/Leave detect karne wala function
@pytgcalls.on_update()
async def vc_participant_update(client, update: Update):
    # Agar update participant ke baare mein nahi hai, toh return kar do
    if not isinstance(update, CallParticipantUpdated):
        return

    chat_id = update.chat_id
    
    # Check karein ki group mein monitoring ON hai ya nahi
    if await is_monitoring_enabled(chat_id):
        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"

        # Jab koi VC JOIN kare
        if update.status == ParticipantStatus.JOINED:
            await app.send_message(
                chat_id, 
                f"🔔 **VC Join Update**\n\nUser: {mention}\nID: `{user_id}` ne VC join kiya hai."
            )

        # Jab koi VC LEAVE kare
        elif update.status == ParticipantStatus.LEFT:
            await app.send_message(
                chat_id, 
                f"🔕 **VC Leave Update**\n\nUser: {mention}\nID: `{user_id}` ne VC leave kar diya hai."
            )

# 3. Command: VC Monitoring ON karne ke liye
@app.on_message(filters.command("vcon") & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply_text("✅ **VC monitoring shuru ho gayi hai!**\nAb koi bhi join/leave karega toh update milega.")

# 4. Command: VC Monitoring OFF karne ke liye
@app.on_message(filters.command("vcoff") & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply_text("❌ **VC monitoring band kar di gayi hai.**")
