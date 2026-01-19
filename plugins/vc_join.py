from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update  # Sirf Update rakha hai
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app

# Pytgcalls ko link kiya
pytgcalls = PyTgCalls(app)

# 1. Database se check karne ke liye ki service ON hai ya nahi
async def is_monitoring_enabled(chat_id):
    status = await mongodb.vc_monitoring.find_one({"chat_id": chat_id})
    return status and status.get("status") == "on"

# 2. VC Join/Leave Monitor
@pytgcalls.on_update()
async def vc_participant_update(client, update: Update):
    # Chat ID check karein
    chat_id = update.chat_id
    if not chat_id:
        return

    # Check karein agar DB mein monitoring ON hai
    if await is_monitoring_enabled(chat_id):
        # Naye pytgcalls mein attributes ko check karne ka tarika
        # Hum check karenge ki update mein user_id hai ya nahi
        user_id = getattr(update, "user_id", None)
        
        if not user_id:
            return

        mention = f"[{user_id}](tg://user?id={user_id})"
        
        # 'status' attribute se pata chalta hai ki join kiya ya leave
        # 'joined' ya 1 ka matlab JOIN, 'left' ya 2 ka matlab LEAVE
        status = str(getattr(update, "status", "")).lower()

        if "joined" in status or status == "1":
            await app.send_message(
                chat_id, 
                f"🔔 **VC Update**\n\nUser: {mention}\nID: `{user_id}` ne VC join kiya."
            )
        elif "left" in status or status == "2":
            await app.send_message(
                chat_id, 
                f"🔕 **VC Update**\n\nUser: {mention}\nID: `{user_id}` ne VC leave kiya."
            )

# 3. Commands
@app.on_message(filters.command("vcon") & filters.group)
async def start_vc_monitor(client, message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply_text("✅ **VC Monitoring ON ho gayi!**")

@app.on_message(filters.command("vcoff") & filters.group)
async def stop_vc_monitor(client, message):
    chat_id = message.chat.id
    await mongodb.vc_monitoring.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply_text("❌ **VC Monitoring OFF ho gayi!**")
