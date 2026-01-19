from pyrogram import Client, filters
from pyrogram.types import Message
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP  # Bot ka main call handler
from pytgcalls.types import Update  # Sirf base Update import kiya

# 1. Database check karne ka function
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# 2. Join/Leave detect karne wala function
@VIP.on_update()
async def vc_participant_update(client, update: Update):
    # Chat ID nikalne ki koshish (Alag-alag version ke liye)
    chat_id = getattr(update, "chat_id", None)
    if not chat_id:
        return

    # Check karein agar DB mein monitoring ON hai
    if await is_monitoring_enabled(chat_id):
        # Update ke andar se user_id aur status nikalna (Dynamic tarika)
        user_id = getattr(update, "user_id", None)
        status = str(getattr(update, "status", "")).lower()

        if not user_id:
            return

        mention = f"[{user_id}](tg://user?id={user_id})"

        # Agar status mein 'join' word hai ya status code 1 hai
        if "join" in status or status == "participant_status.joined" or status == "1":
            await app.send_message(
                chat_id, 
                f"🔔 **VC Update**\n\nUser: {mention}\nID: `{user_id}` ne VC join kiya."
            )

        # Agar status mein 'leave' ya 'left' word hai ya status code 2 hai
        elif "left" in status or "leave" in status or status == "participant_status.left" or status == "2":
            await app.send_message(
                chat_id, 
                f"🔕 **VC Update**\n\nUser: {mention}\nID: `{user_id}` ne VC leave kiya."
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
    await message.reply_text("✅ **VC Monitoring ON ho gayi!**")

@app.on_message(filters.command(["vcoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply_text("❌ **VC Monitoring OFF ho gayi!**")
