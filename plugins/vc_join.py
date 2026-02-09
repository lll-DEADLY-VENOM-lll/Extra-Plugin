from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP
import asyncio

# MongoDB collection
db = mongodb.vc_monitoring

# MongoDB check function (Safe handling)
async def is_monitoring_enabled(chat_id):
    try:
        status = await db.find_one({"chat_id": chat_id})
        return status is not None and status.get("status") == "on"
    except Exception:
        return False

# VC Participants Handler
@VIP.one.on_participants_change()
async def vc_participants_handler(client, update):
    chat_id = getattr(update, "chat_id", None)
    if not chat_id or not await is_monitoring_enabled(chat_id):
        return

    user_id = None
    action_text = ""

    if isinstance(update, JoinedGroupCallParticipant):
        user_id = update.participant.user_id
        action_text = "ne VC join kiya. 👤"
    elif isinstance(update, LeftGroupCallParticipant):
        user_id = update.participant.user_id
        action_text = "ne VC leave kiya. 🏃"

    if user_id:
        try:
            # User details fetch karna (Username ke liye)
            user = await app.get_users(user_id)
            if user:
                name = user.first_name if user.first_name else "User"
                username = f"@{user.username}" if user.username else "N/A"
                mention = f"[{name}](tg://user?id={user_id})"
                
                msg_text = (
                    f"{mention} {action_text}\n"
                    f"**👤 Name:** {name}\n"
                    f"**🔗 Username:** {username}\n"
                    f"**🆔 User ID:** `{user_id}`"
                )
            else:
                msg_text = f"User ID: `{user_id}` {action_text}"

            await app.send_message(chat_id, msg_text)
        except Exception as e:
            # Agar user details na milein toh sirf ID bhej do
            print(f"User Fetch Error: {e}")
            try:
                await app.send_message(chat_id, f"Ek user (`{user_id}`) {action_text}")
            except:
                pass

# --- Commands with Safety Checks (Flood Detector Fix) ---

@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    # Fix: Check if chat and from_user exist to avoid NoneType error
    if not message or not message.chat:
        return
    
    # Optional: Check if the message is from a user (not a channel/anonymous)
    user_id = message.from_user.id if message.from_user else "Anonymous"
    
    chat_id = message.chat.id
    try:
        await db.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "on"}},
            upsert=True
        )
        await message.reply_text(f"✅ **VC Monitoring ON**\nAb participants track honge.")
    except Exception as e:
        print(f"Error: {e}")

@app.on_message(filters.command(["vclogoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    if not message or not message.chat:
        return
        
    chat_id = message.chat.id
    try:
        await db.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "off"}},
            upsert=True
        )
        await message.reply_text("❌ **VC Monitoring OFF.**")
    except Exception as e:
        print(f"Error: {e}")
