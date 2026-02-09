from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls.types import JoinedGroupCallParticipant, LeftGroupCallParticipant
from VIPMUSIC.core.mongo import mongodb 
from VIPMUSIC import app
from VIPMUSIC.core.call import VIP

# MongoDB collection
db = mongodb.vc_monitoring

# MongoDB check function (Safely handled)
async def is_monitoring_enabled(chat_id):
    if not chat_id:
        return False
    try:
        status = await db.find_one({"chat_id": chat_id})
        return status is not None and status.get("status") == "on"
    except:
        return False

# VC Participants Handler (Join/Leave track karne ke liye)
@VIP.one.on_participants_change()
async def vc_participants_handler(client, update):
    # Fix: Safely get chat_id from update
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
            # Username fetch karne ke liye user details nikalna
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

            await app.send_message(chat_id, final_text)
            
        except Exception as e:
            # Agar bot user details fetch na kar paye toh sirf ID bhej dega
            print(f"Error fetching user in VC: {e}")
            try:
                await app.send_message(chat_id, f"User ID `{user_id}` {action_text}")
            except:
                pass

# --- COMMANDS SECTION WITH FLOOD & NONETYPE FIX ---

@app.on_message(filters.command(["vclogon", "checkvcon"]) & filters.group)
async def start_vc_monitor(client: Client, message: Message):
    # Fix 1: Check if message and chat exist
    if not message or not message.chat:
        return
    
    # Fix 2: Anonymous Admin handling (from_user is None)
    if not message.from_user:
        # Agar anonymous admin hai, toh hum sirf chat_id process karenge bina error ke
        pass 

    chat_id = message.chat.id
    try:
        await db.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": "on"}},
            upsert=True
        )
        await message.reply_text(f"✅ **VC Monitoring ON**\nAb participants track kiye jayenge.")
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
        await message.reply_text("❌ **VC Monitoring OFF.**")
    except Exception as e:
        print(f"Error in vclogoff: {e}")
