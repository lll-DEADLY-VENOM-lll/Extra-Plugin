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
    except:
        return False
    return False

# VC Participants Handler (Jo Join/Leave Track karega)
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
            # User details fetch karna username nikalne ke liye
            user = await app.get_users(user_id)
            name = user.first_name if user.first_name else "User"
            username = f"@{user.username}" if user.username else "N/A"
            mention = f"[{name}](tg://user?id={user_id})"

            text = (
                f"{mention} {action_text}\n"
                f"**👤 Name:** {name}\n"
                f"**🔗 Username:** {username}\n"
                f"**🆔 User ID:** `{user_id}`"
            )
            
            await app.send_message(chat_id, text)
        except Exception as e:
            # Agar bot user fetch nahi kar paya (flood error ya koi aur reason)
            print(f"Error fetching user: {e}")
            try:
                await app.send_message(chat_id, f"Ek user (`{user_id}`) {action_text}")
            except:
                pass

# --- COMMANDS SECTION WITH CRASH FIX ---

@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    # CRASH FIX: Check if message has a sender (from_user)
    if not message.from_user:
        return
    
    chat_id = message.chat.id
    try:
        await db.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "on"}},
            upsert=True
        )
        await message.reply_text(f"✅ **VC Monitoring ON**\nAssistant ab is group ke participants ko track karega.")
    except Exception as e:
        print(f"Error in vclogon: {e}")

@app.on_message(filters.command(["vclogoff", "checkvcoff"]) & filters.group)
async def stop_vc_monitor(client: Client, message: Message):
    # CRASH FIX: Check if message has a sender (from_user)
    if not message.from_user:
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
        print(f"Error in vclogoff: {e}")
