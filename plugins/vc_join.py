from pyrogram import Client, filters
from pyrogram.types import Message
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP  # Bot ka main call handler
from pytgcalls.types import Update  # Base Update

# 1. Database check function
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# 2. Join/Leave detect karne wala function
# VIP-MUSIC mein aksar 'call' attribute ke andar PyTgCalls hota hai
@VIP.calls.on_update()
async def vc_participant_update(client, update: Update):
    # Chat ID nikalna
    chat_id = getattr(update, "chat_id", None)
    if not chat_id:
        return

    # Check status from DB
    if await is_monitoring_enabled(chat_id):
        user_id = getattr(update, "user_id", None)
        if not user_id:
            return

        # Status check (Joins/Leaves)
        status = str(getattr(update, "status", "")).lower()
        mention = f"[{user_id}](tg://user?id={user_id})"

        # Join detection
        if "join" in status or status == "1":
            try:
                await app.send_message(
                    chat_id, 
                    f"🔔 **VC Update**\n\nUser: {mention}\nID: `{user_id}` ne VC join kiya."
                )
            except:
                pass

        # Leave detection
        elif "left" in status or "leave" in status or status == "2":
            try:
                await app.send_message(
                    chat_id, 
                    f"🔕 **VC Update**\n\nUser: {mention}\nID: `{user_id}` ne VC leave kiya."
                )
            except:
                pass

# 3. Commands
@app.on_message(filters.command(["vcon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client, message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply_text("✅ **VC Monitoring ON ho gayi hai!**")

@app.on_message(filters.command(["vcoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client, message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply_text("❌ **VC Monitoring OFF ho gayi hai.**")
