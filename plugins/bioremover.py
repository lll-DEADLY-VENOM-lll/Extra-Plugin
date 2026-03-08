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

Yeh module group ko spam se bachata hai. Agar kisi user ke profile bio mein link hoga, toh bot unhe message karne se rokega.

<b>Strike System:</b>
• Pehli 2 baar message delete hoga aur warning di jayegi.
• Teesri (3rd) baar link ke saath message karne par user ko <b>Mute</b> kar diya jayega.

<b>Admin Commands:</b>
• /approve - Kisi user ke message par reply karke use whitelist karein (woh link ke sath bhi message kar payega).
• /unapprove - Reply karke user ko whitelist se hatayein.

<i>Note: Bot ko Admin banana aur Delete Messages/Ban Users permission dena zaroori hai.</i>
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

# Main Message Handler
@app.on_message(filters.group & ~filters.service, group=10)
async def bio_remover_handler(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # 1. Skip Admins and Approved Users
    if user_id in approved_users or await is_admin(chat_id, user_id):
        return

    # 2. Check Bio
    try:
        full_user = await client.get_users(user_id)
        bio = full_user.bio if full_user.bio else ""
        
        # Agar bio mein link ya username mile
        if re.search(URL_PATTERN, bio, re.IGNORECASE):
            
            # Update warning count
            current_warns = warning_count.get(user_id, 0) + 1
            warning_count[user_id] = current_warns

            if current_warns < 3:
                # Pehli aur doosri baar sirf delete aur warning
                try:
                    await message.delete()
                except:
                    pass
                
                warn_text = f"⚠️ {message.from_user.mention}, aapke bio mein link hai. Message allow nahi hai. (Warning: {current_warns}/3)"
                warn_msg = await message.reply(warn_text)
                
                # 5 second baad warning message delete karein taaki chat saaf rahe
                await asyncio.sleep(5)
                try:
                    await warn_msg.delete()
                except:
                    pass
            
            else:
                # Teesre message par Mute
                try:
                    await message.delete()
                    await client.restrict_chat_member(
                        chat_id, 
                        user_id, 
                        ChatPermissions(can_send_messages=False)
                    )
                    await message.reply_text(
                        f"🚫 {message.from_user.mention} ko mute kar diya gaya hai. "
                        f"Kyunki unhone bio link ke saath 3 baar message karne ki koshish ki."
                    )
                except Exception as e:
                    print(f"Mute Error: {e}")
                
                # Strike reset karein mute ke baad
                warning_count[user_id] = 0

    except Exception as e:
        # User details fetch karne mein error (profile privacy ki wajah se ho sakta hai)
        print(f"Bio Check Error: {e}")

# Command: /approve
@app.on_message(filters.command("approve") & filters.group)
async def approve_user_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply("Sirf Admins hi approve kar sakte hain.")
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        approved_users.add(target_id)
        
        # Unmute if previously restricted
        try:
            await client.restrict_chat_member(message.chat.id, target_id, ChatPermissions(can_send_messages=True))
        except:
            pass
        
        await message.reply(f"✅ {message.reply_to_message.from_user.first_name} ko approve kar diya gaya hai. Ab yeh link ke sath message kar sakte hain.")
    else:
        await message.reply("Kisi user ke message par reply karke `/approve` likhein.")

# Command: /unapprove
@app.on_message(filters.command("unapprove") & filters.group)
async def unapprove_user_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id in approved_users:
            approved_users.remove(target_id)
            await message.reply("❌ User ko whitelist se hata diya gaya hai.")
        else:
            await message.reply("Yeh user pehle se approved list mein nahi hai.")
    else:
        await message.reply("Reply to a user to unapprove them.")
