from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, enums  # Yaha change hai
from pytgcalls.types import Update
from VIPMUSIC.core.mongo import mongodb
from VIPMUSIC import app
# Check karein ki aapka pytgcalls instance VIP hai ya call
from VIPMUSIC.core.call import VIP as pytgcalls 

# Function to check monitoring status (Async because of Motor/MongoDB)
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# Event handler for VC updates
@pytgcalls.on_update()
async def vc_participant_update(client, update: Update):
    # Naye version mein update_type directly enums se check hota hai
    if update.update_type == enums.UpdateType.PARTICIPANT_JOINED:
        chat_id = update.chat_id
        if not await is_monitoring_enabled(chat_id):
            return
        
        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"
        await app.send_message(chat_id, f"✅ **VC Join Update**\n\n👤 {mention} ne VC join kiya.\n🆔 ID: `{user_id}`")

    elif update.update_type == enums.UpdateType.PARTICIPANT_LEFT:
        chat_id = update.chat_id
        if not await is_monitoring_enabled(chat_id):
            return
            
        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"
        await app.send_message(chat_id, f"❌ **VC Leave Update**\n\n👤 {mention} ne VC leave kiya.\n🆔 ID: `{user_id}`")

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
        await message.reply("✅ VC Monitoring ON ho gayi hai.")
    elif state == "off":
        await mongodb.vc_monitoring.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "off"}},
            upsert=True
        )
        await message.reply("❌ VC Monitoring OFF ho gayi hai.")
