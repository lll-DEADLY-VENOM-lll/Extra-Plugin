from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP

# MongoDB collection
db = mongodb.vc_monitoring

# MongoDB check function (Simplified & Fixed)
async def is_monitoring_enabled(chat_id):
    try:
        # VIP Music mein mongodb usually motor-asyncio hota hai
        status = await db.find_one({"chat_id": chat_id})
        if status and status.get("status") == "on":
            return True
    except Exception as e:
        print(f"Error checking DB: {e}")
    return False

# VC Participants Handler
@VIP.one.on_participants_change()
async def vc_participants_handler(client, update):
    chat_id = update.chat_id
    
    # Check if monitoring is ON
    if not await is_monitoring_enabled(chat_id):
        return

    user_id = None
    action_text = ""

    # User Join Check
    if isinstance(update, JoinedGroupCallParticipant):
        user_id = update.participant.user_id
        action_text = "ne VC join kiya. 👤"

    # User Leave Check
    elif isinstance(update, LeftGroupCallParticipant):
        user_id = update.participant.user_id
        action_text = "ne VC leave kiya. 🏃"

    if user_id:
        try:
            mention = f"[{user_id}](tg://user?id={user_id})"
            # Message send logic
            await app.send_message(
                chat_id, 
                f"{mention} {action_text}\n**User ID:** `{user_id}`"
            )
        except Exception as e:
            print(f"Failed to send message: {e}")

# Commands to turn ON/OFF
@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    if not message.chat:
        return
    chat_id = message.chat.id
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply("✅ **VC Monitoring ON:** Assistant ab participants ko track karega.")

@app.on_message(filters.command(["vclogoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    if not message.chat:
        return
    chat_id = message.chat.id
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply("❌ **VC Monitoring OFF.**")
