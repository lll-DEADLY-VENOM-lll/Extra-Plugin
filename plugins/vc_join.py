from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.enums import UpdateType
from VIPMUSIC.core.mongo import mongodb
from VIPMUSIC import app
# Apne instance ka sahi path dein (e.g., from VIPMUSIC import call)
from VIPMUSIC.core.call import VIP as pytgcalls 

# Function to check monitoring status
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# Main Event Handler
@pytgcalls.on_update()
async def vc_participant_update(client, update: Update):
    # Check if this update is about a participant joining or leaving
    if update.update_type in [UpdateType.PARTICIPANT_JOINED, UpdateType.PARTICIPANT_LEFT]:
        chat_id = update.chat_id
        
        # Database check
        if not await is_monitoring_enabled(chat_id):
            return

        user_id = update.user_id
        mention = f"[{user_id}](tg://user?id={user_id})"

        if update.update_type == UpdateType.PARTICIPANT_JOINED:
            msg = f"✅ **VC Join Update**\n\n👤 **User:** {mention}\n🆔 **ID:** `{user_id}`\n\nVC join kiya gaya hai."
        else:
            msg = f"❌ **VC Leave Update**\n\n👤 **User:** {mention}\n🆔 **ID:** `{user_id}`\n\nVC leave kar diya gaya hai."

        try:
            await app.send_message(chat_id, msg)
        except Exception as e:
            print(f"Error sending message: {e}")

# Command to Start/Stop
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
        await message.reply("⚡️ **VC Monitoring Enabled!**\nAb koi bhi join ya leave karega toh update mil jayega.")
    
    elif state == "off":
        await mongodb.vc_monitoring.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "off"}},
            upsert=True
        )
        await message.reply("🔕 **VC Monitoring Disabled!**")
    
    else:
        await message.reply("Invalid Option! Use `on` or `off`.")
