from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update, UserJoined, UserLeft
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app

# 1. Pytgcalls ko app ke saath connect kiya
pytgcalls = PyTgCalls(app)

# 2. Check karne ke liye ki monitoring ON hai ya nahi
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# 3. Join/Leave detect karne wala function
@pytgcalls.on_update()
async def vc_participant_update(client, update: Update):
    chat_id = update.chat_id
    
    # Check status from DB
    if await is_monitoring_enabled(chat_id):
        if isinstance(update, UserJoined):
            user_id = update.user_id
            mention = f"[{user_id}](tg://user?id={user_id})"
            await app.send_message(chat_id, f"🔔 {mention} ne VC join kiya hai.")

        elif isinstance(update, UserLeft):
            user_id = update.user_id
            mention = f"[{user_id}](tg://user?id={user_id})"
            await app.send_message(chat_id, f"🔕 {mention} ne VC leave kar diya.")

# 4. Monitoring ON karne ka command
@app.on_message(filters.command("vcon") & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply("✅ VC monitoring shuru ho gayi hai!")

# 5. Monitoring OFF karne ka command
@app.on_message(filters.command("vcoff") & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply("❌ VC monitoring band kar di gayi hai.")
