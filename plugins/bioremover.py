import re
import asyncio
from pyrogram import filters
from pyrogram.types import ChatPermissions

# VIP-MUSIC ke existing app ko import karein
from VIPMUSIC import app

# Memory storage (Bot restart par reset ho jayega)
approved_users = set()    
warning_count = {}        

# Link detect karne ke liye Regex
URL_PATTERN = r"(https?://\S+|www\.\S+|t\.me/\S+|\.com|\.in|\.net|\.org|@)"

# Admin check function
async def is_admin(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

@app.on_message(filters.group & ~filters.service, group=10) # group=10 taaki dusre plugins se clash na ho
async def bio_remover_handler(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # 1. Approved users ya Admins ko ignore karein
    if user_id in approved_users or await is_admin(chat_id, user_id):
        return

    # 2. Bio check logic
    try:
        full_user = await client.get_users(user_id)
        bio = full_user.bio if full_user.bio else ""
        
        if re.search(URL_PATTERN, bio, re.IGNORECASE):
            # Strike System
            current_warns = warning_count.get(user_id, 0) + 1
            warning_count[user_id] = current_warns

            if current_warns < 3:
                # Strike 1 & 2: Delete + Warning
                try:
                    await message.delete()
                except:
                    pass
                
                warn_text = f"⚠️ {message.from_user.mention}, aapke bio mein link hai. Message allow nahi hai. (Warning: {current_warns}/3)"
                warn_msg = await message.reply(warn_text)
                
                await asyncio.sleep(5)
                try:
                    await warn_msg.delete()
                except:
                    pass
            
            else:
                # Strike 3: Delete + Mute
                try:
                    await message.delete()
                    await client.restrict_chat_member(
                        chat_id, 
                        user_id, 
                        ChatPermissions(can_send_messages=False)
                    )
                    await message.reply_text(
                        f"🚫 {message.from_user.mention} ko mute kar diya gaya hai. "
                        f"Bio link ke saath 3 baar message karne ki wajah se."
                    )
                except Exception as e:
                    print(f"Mute Error: {e}")
                
                warning_count[user_id] = 0

    except Exception as e:
        print(f"Bio Check Error: {e}")

# Command: /approve (Reply to user)
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
        
        await message.reply(f"✅ User approved! Ab yeh bio link ke sath message kar sakte hain.")
    else:
        await message.reply("Kisi ke message par reply karke `/approve` likhein.")

# Command: /unapprove
@app.on_message(filters.command("unapprove") & filters.group)
async def unapprove_user_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id in approved_users:
            approved_users.remove(target_id)
            await message.reply("❌ User approved list se hata diya gaya.")
