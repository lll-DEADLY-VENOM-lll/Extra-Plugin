import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP

# MongoDB collection
db = mongodb.vc_monitoring

# MongoDB check function
async def is_monitoring_enabled(chat_id):
    if not chat_id:
        return False
    try:
        status = await db.find_one({"chat_id": chat_id})
        return status is not None and status.get("status") == "on"
    except:
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
            user = await app.get_users(user_id)
            if user:
                name = user.first_name or "User"
                username = f"@{user.username}" if user.username else "N/A"
                mention = f"[{name}](tg://user?id={user_id})"
                
                final_text = (
                    f"{mention} {action_text}\n"
                    f"**👤 Name:** {name}\n"
                    f"**🔗 Username:** {username}\n"
                    f"**🆔 User ID:** `{user_id}`"
                )
            else:
                final_text = f"User ID `{user_id}` {action_text}"

            # Message bhejna aur 15 second baad delete karna
            sent_msg = await app.send_message(chat_id, final_text)
            await asyncio.sleep(15)
            await sent_msg.delete()
            
        except Exception as e:
            print(f"Error in VC Logger: {e}")

# --- COMMANDS SECTION ---

@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    if not message or not message.chat:
        return
    
    chat_id = message.chat.id
    try:
        await db.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "on"}},
            upsert=True
        )
        msg = await message.reply_text(f"✅ **VC Monitoring ON**\n\nAb participants track kiye jayenge. (Ye message 15s mein delete ho jayega)")
        await asyncio.sleep(15)
        await msg.delete()
        await message.delete() # User ka command bhi delete ho jayega
    except Exception as e:
        print(f"Error in vclogon: {e}")

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
        msg = await message.reply_text("❌ **VC Monitoring OFF.**\n\nAb alerts nahi milenge.")
        await asyncio.sleep(15)
        await msg.delete()
        await message.delete()
    except Exception as e:
        print(f"Error in vclogoff: {e}")
