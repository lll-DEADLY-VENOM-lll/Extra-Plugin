from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP
import asyncio

# MongoDB check function
async def is_monitoring_enabled(chat_id):
    status = await asyncio.to_thread(mongodb.vc_monitoring.find_one, {"chat_id": chat_id})
    return status and status.get("status") == "on"

# VC Participants Handler
@VIP.one.on_participants_change()
async def vc_participants_handler(client, update):
    chat_id = update.chat_id
    
    # Check if monitoring is ON
    if not await is_monitoring_enabled(chat_id):
        return

    user_id = None
    text = ""

    # User Join Check
    if isinstance(update, JoinedGroupCallParticipant):
        user_id = update.participant.user_id
        text = f"👤 [User](tg://user?id={user_id}) ne VC join kiya.\n**User ID:** `{user_id}`"

    # User Leave Check
    elif isinstance(update, LeftGroupCallParticipant):
        user_id = update.participant.user_id
        text = f"🏃 [User](tg://user?id={user_id}) ne VC leave kiya.\n**User ID:** `{user_id}`"

    if user_id:
        try:
            # Bot (app) se message bhej rahe hain
            await app.send_message(chat_id, text)
        except Exception as e:
            print(f"Error sending VC log: {e}")

# Commands to turn ON
@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply("✅ **VC Monitoring ON:** Assistant ab participants ko track karega.")

# Command to turn OFF
@app.on_message(filters.command(["vclogoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply("❌ **VC Monitoring OFF.**")
