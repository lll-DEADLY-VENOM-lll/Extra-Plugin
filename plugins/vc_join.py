from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import Update, CallParticipantUpdated
from pytgcalls.types.enums import ParticipantStatus
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP  # Bot ka pehle se bana hua call handler import kiya

# 1. Database check karne ka function
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# 2. Join/Leave detect karne wala function
# Hum 'pytgcalls' ki jagah 'VIP' (bot ka default handler) use karenge
@VIP.on_update()
async def vc_participant_update(client, update: Update):
    # Check karein agar update participant ke baare mein hai
    if not isinstance(update, CallParticipantUpdated):
        return

    chat_id = update.chat_id
    
    # DB status check karein
    if await is_monitoring_enabled(chat_id):
        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"

        # Jab koi Join kare
        if update.status == ParticipantStatus.JOINED:
            await app.send_message(
                chat_id, 
                f"🔔 **VC Join Update**\n\nUser: {mention}\nID: `{user_id}` ne VC join kiya."
            )

        # Jab koi Leave kare
        elif update.status == ParticipantStatus.LEFT:
            await app.send_message(
                chat_id, 
                f"🔕 **VC Leave Update**\n\nUser: {mention}\nID: `{user_id}` ne VC leave kiya."
            )

# 3. Commands
@app.on_message(filters.command(["vcon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply_text(f"✅ **VC Monitoring ON kar di gayi hai.**")

@app.on_message(filters.command(["vcoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply_text(f"❌ **VC Monitoring OFF kar di gayi hai.**")
