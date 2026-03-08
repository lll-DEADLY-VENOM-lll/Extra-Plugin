import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions

# Config file se data import kar rahe hain
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("BioGuardBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Memory storage (Note: Bot restart hone par yeh khali ho jayega)
approved_users = set()    # Approved user IDs ki list
warning_count = {}        # {user_id: count} strike system ke liye

# Link detect karne ke liye Regex
URL_PATTERN = r"(https?://\S+|www\.\S+|t\.me/\S+|\.com|\.in|\.net|\.org|@)"

# Admin check function
async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

@app.on_message(filters.group & ~filters.service)
async def check_bio_handler(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # 1. Approved users ya Admins ko check nahi karna
    if user_id in approved_users or await is_admin(client, chat_id, user_id):
        return

    # 2. User ka bio check karein
    try:
        full_user = await client.get_users(user_id)
        bio = full_user.bio if full_user.bio else ""
        
        # Agar bio mein link ya username hai
        if re.search(URL_PATTERN, bio, re.IGNORECASE):
            
            # Counter check karein (Strike System)
            current_warns = warning_count.get(user_id, 0) + 1
            warning_count[user_id] = current_warns

            if current_warns < 3:
                # 1st aur 2nd strike: Message delete + Warning
                await message.delete()
                warn_text = f"⚠️ {message.from_user.mention}, aapke bio mein link hai. Message allow nahi hai. (Warning: {current_warns}/3)"
                warn_msg = await message.reply(warn_text)
                
                # 5 second baad warning message delete karein (Chat clean rakhne ke liye)
                await asyncio.sleep(5)
                await warn_msg.delete()
            
            else:
                # 3rd strike: Message delete + Mute
                await message.delete()
                await client.restrict_chat_member(
                    chat_id, 
                    user_id, 
                    ChatPermissions(can_send_messages=False)
                )
                await message.reply_text(
                    f"🚫 {message.from_user.mention} ko mute kar diya gaya hai. "
                    f"Unhone 3 baar bio link ke saath message bhejne ki koshish ki."
                )
                # Strike reset karein mute ke baad
                warning_count[user_id] = 0

    except Exception as e:
        print(f"Error checking bio: {e}")

# Command: Approve user (Reply karke /approve)
@app.on_message(filters.command("approve") & filters.group)
async def approve_cmd(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("Sirf admins approve kar sakte hain.")
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
        
        approved_users.add(target_id)
        
        # Agar user mute tha toh unmute karein
        try:
            await client.restrict_chat_member(message.chat.id, target_id, ChatPermissions(can_send_messages=True))
        except:
            pass
        
        await message.reply(f"✅ {target_name} ko approve kar diya gaya hai. Ab yeh message kar sakte hain.")
    else:
        await message.reply("User ke message par reply karke `/approve` likhein.")

# Command: Unapprove user (Reply karke /unapprove)
@app.on_message(filters.command("unapprove") & filters.group)
async def unapprove_cmd(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id in approved_users:
            approved_users.remove(target_id)
            await message.reply("❌ User ko approved list se hata diya gaya hai.")

print("Bot Start Ho Gaya Hai...")
app.run()
