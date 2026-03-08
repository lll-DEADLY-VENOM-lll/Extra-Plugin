import re
import asyncio
from pyrogram import filters
from pyrogram.types import ChatPermissions

# VIP-MUSIC ke existing app ko import karein
from VIPMUSIC import app

# --- MODULE METADATA ---
__MODULE__ = "Bio Remover"
__HELP__ = """
<b><u>Bio Link Protector</u></b>

Yeh module un logo ko rokta hai jinke bio (description) mein link hota hai.

<b>Features:</b>
• Link milne par message delete hota hai.
• Bot user ko tag karke warning deta hai.
• 3 strikes ke baad user ko Mute kar diya jata hai.

<b>Commands:</b>
• /approve - Reply karke user ko allow karein.
• /unapprove - Reply karke whitelist se hatayein.
"""

# Memory storage
approved_users = set()    
warning_count = {}        

# Link detect karne ke liye Regex
URL_PATTERN = r"(https?://\S+|www\.\S+|t\.me/\S+|\.com|\.in|\.net|\.org|@)"

# Admin check helper
async def is_admin(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

# Main Handler
@app.on_message(filters.group & ~filters.service, group=10)
async def bio_remover_handler(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    username = f"@{message.from_user.username}" if message.from_user.username else "No Username"

    # 1. Skip Admins and Approved Users
    if user_id in approved_users or await is_admin(chat_id, user_id):
        return

    # 2. Check Bio (Description)
    try:
        full_user_chat = await client.get_chat(user_id)
        bio = full_user_chat.description if full_user_chat.description else ""
        
        if re.search(URL_PATTERN, bio, re.IGNORECASE):
            # Message delete karein
            try:
                await message.delete()
            except:
                pass
            
            # Strike System logic
            current_warns = warning_count.get(user_id, 0) + 1
            warning_count[user_id] = current_warns

            if current_warns < 3:
                # User ko tag karke message bhejein
                warn_text = (
                    f"⚠️ <b>Link Detected in Bio!</b>\n\n"
                    f"👤 <b>User:</b> {message.from_user.mention}\n"
                    f"🆔 <b>Username:</b> {username}\n\n"
                    f"❌ Aapka message delete kar diya gaya hai kyunki aapke bio mein link hai. "
                    f"Kripya link hatayein warna aapko mute kar diya jayega.\n"
                    f"🚩 <b>Warning:</b> {current_warns}/3"
                )
                warn_msg = await client.send_message(chat_id, warn_text)
                
                # 8 second baad warning message delete karein taaki chat saaf rahe
                await asyncio.sleep(8)
                try:
                    await warn_msg.delete()
                except:
                    pass
            
            else:
                # 3rd strike par Mute
                try:
                    await client.restrict_chat_member(
                        chat_id, 
                        user_id, 
                        ChatPermissions(can_send_messages=False)
                    )
                    await client.send_message(
                        chat_id,
                        f"🚫 <b>User Muted!</b>\n\n"
                        f"👤 {message.from_user.mention} ({username}) ko permanently mute kar diya gaya hai. "
                        f"Kyunki unhone bio link ke saath baar-baar message bhejne ki koshish ki."
                    )
                except Exception as e:
                    print(f"Mute Error: {e}")
                
                warning_count[user_id] = 0

    except Exception as e:
        print(f"Bio Check Error: {e}")

# Command: /approve
@app.on_message(filters.command("approve") & filters.group)
async def approve_user_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        approved_users.add(target_id)
        
        try:
            await client.restrict_chat_member(message.chat.id, target_id, ChatPermissions(can_send_messages=True))
        except:
            pass
        
        await message.reply(f"✅ {message.reply_to_message.from_user.mention} ko whitelist mein add kar diya gaya hai.")
    else:
        await message.reply("Reply to a user to approve them.")

# Command: /unapprove
@app.on_message(filters.command("unapprove") & filters.group)
async def unapprove_user_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id in approved_users:
            approved_users.remove(target_id)
            await message.reply(f"❌ {message.reply_to_message.from_user.mention} ko whitelist se hata diya gaya.")
