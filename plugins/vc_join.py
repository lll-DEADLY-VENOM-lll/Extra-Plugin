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
    try:
        status = await db.find_one({"chat_id": chat_id})
        if status and status.get("status") == "on":
            return True
    except Exception:
        return False
    return False

# VC Participants Handler
@VIP.one.on_participants_change()
async def vc_participants_handler(client, update):
    chat_id = update.chat_id
    
    if not await is_monitoring_enabled(chat_id):
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
            # User details nikalne ke liye
            user = await app.get_users(user_id)
            
            # Agar user mil gaya toh details set karein
            if user:
                first_name = user.first_name if user.first_name else "User"
                username = f"@{user.username}" if user.username else "N/A"
                mention = f"[{first_name}](tg://user?id={user_id})"
                
                text = (
                    f"{mention} {action_text}\n"
                    f"**👤 Name:** {first_name}\n"
                    f"**🔗 Username:** {username}\n"
                    f"**🆔 User ID:** `{user_id}`"
                )
            else:
                text = f"Ek user (`{user_id}`) {action_text}"

            await app.send_message(chat_id, text)
            
        except Exception as e:
            # Agar koi error aaye (jaise flood limit ya user not found)
            print(f"Error in VC handler: {e}")
            try:
                await app.send_message(chat_id, f"Ek user (`{user_id}`) {action_text}")
            except:
                pass

# Command: VC Monitor ON
@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    # Safety check: error prevention
    if not message or not message.chat:
        return
    
    # Check if user is admin (optional but recommended)
    chat_id = message.chat.id
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "on"}},
        upsert=True
    )
    await message.reply_text(f"✅ **VC Monitoring ON** in {message.chat.title}")

# Command: VC Monitor OFF
@app.on_message(filters.command(["vclogoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    if not message or not message.chat:
        return
        
    chat_id = message.chat.id
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"status": "off"}},
        upsert=True
    )
    await message.reply_text(f"❌ **VC Monitoring OFF** in {message.chat.title}")
