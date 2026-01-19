from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import UpdateType  # Yaha change kiya hai
from VIPMUSIC.core.mongo import mongodb
from VIPMUSIC import app
# Check karein aapka call instance kis naam se hai (VIP ya kuch aur)
from VIPMUSIC.core.call import VIP as pytgcalls 

# Function to check monitoring status
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# Event handler for VC updates
@pytgcalls.on_update()
async def vc_participant_update(client, update: Update):
    # Version 1.2.9 mein UpdateType.PARTICIPANT_JOINED use hota hai
    if update.update_type == UpdateType.PARTICIPANT_JOINED:
        chat_id = update.chat_id
        
        if not await is_monitoring_enabled(chat_id):
            return
        
        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"
        
        try:
            await app.send_message(chat_id, f"✅ **VC Join Update**\n\n👤 {mention} ne VC join kiya.\n🆔 ID: `{user_id}`")
        except Exception:
            pass

    elif update.update_type == UpdateType.PARTICIPANT_LEFT:
        chat_id = update.chat_id
        
        if not await is_monitoring_enabled(chat_id):
            return
            
        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"
        
        try:
            await app.send_message(chat_id, f"❌ **VC Leave Update**\n\n👤 {mention} ne VC leave kiya.\n🆔 ID: `{user_id}`")
        except Exception:
            pass

# Commands
@app.on_message(filters.command(["checkvc", "vcmon"]) & filters.group)
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
        await message.reply("✅ **VC Monitoring ON** ho gayi hai.")
    elif state == "off":
        await mongodb.vc_monitoring.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "off"}},
            upsert=True
        )
        await message.reply("❌ **VC Monitoring OFF** ho gayi hai.")
