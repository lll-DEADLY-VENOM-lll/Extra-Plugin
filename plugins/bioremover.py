import re
import asyncio
import time
from pyrogram import filters
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError

# VIP-MUSIC ki existing app aur config import
from VIPMUSIC import app
from config import SUPPORT_CHAT, SUPPORT_CHANNEL

# --- MODULE METADATA (Framework compatibility) ---
__MODULE__ = "Bio Remover"
__HELP__ = """
<b><u>Bio Link Protector</u></b>

Yeh module group ko un spammer se bachata hai jinke bio mein links hote hain.

<b>⚡ Strikes System:</b>
• Pehle 2 messages par: Bot message delete karke user ko warn karega.
• 3rd strike par: User ko permanently group mein mute kar diya jayega.

<b>📡 Commands:</b>
• /ping - Bot ki latency aur status check karne ke liye.
• /approve - User ke message par reply karke whitelist mein add karein.
• /unapprove - User ko whitelist se hatayein.

<b>Note:</b> Bot ko Admin bana kar 'Delete Messages' aur 'Ban Users' permission dena zaroori hai.
"""

# In-memory storage (Restart par reset hoga)
approved_users = set()    
warning_count = {}        

# Link detect karne ke liye pattern
URL_PATTERN = r"(https?://\S+|www\.\S+|t\.me/\S+|\.com|\.in|\.net|\.org|@|telegram\.me/\S+)"

# Inline Buttons generator using Config variables
def support_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Channel", url=SUPPORT_CHANNEL),
            InlineKeyboardButton("👥 Support", url=SUPPORT_CHAT)
        ]
    ])

# Admin check function
async def is_admin(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

# --- [PING COMMAND] ---
@app.on_message(filters.command("ping"))
async def ping_handler(client, message):
    start_time = time.time()
    # Edit text simulation for speed check
    m = await message.reply_text("✨ Pinging...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    await m.edit_text(
        f"<b>🚀 Pong!</b>\n<code>Latency: {ping_time} ms</code>",
        reply_markup=support_buttons()
    )

# --- [MAIN BIO CHECK LOGIC] ---
@app.on_message(filters.group & ~filters.service, group=10)
async def bio_remover_handler(client, message):
    if not message.from_user or message.from_user.is_bot:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    username = f"@{message.from_user.username}" if message.from_user.username else "User"

    # 1. Skip if Admin or Whitelisted
    if user_id in approved_users or await is_admin(chat_id, user_id):
        return

    # 2. Extract Bio using get_chat.description
    try:
        full_user = await client.get_chat(user_id)
        bio = full_user.description if full_user.description else ""
        
        # Agar link mila bio mein
        if re.search(URL_PATTERN, bio, re.IGNORECASE):
            
            # Step A: Delete the original message
            try:
                await message.delete()
            except RPCError:
                # Permission nahi hogi toh bot warn karke rukk jayega
                return

            # Step B: Manage Strike System
            current_strike = warning_count.get(user_id, 0) + 1
            warning_count[user_id] = current_strike

            if current_strike < 3:
                # Send Warning with Tag and Username
                warn_text = (
                    f"⚠️ <b>Link Found in Bio!</b>\n\n"
                    f"👤 <b>Name:</b> {message.from_user.mention}\n"
                    f"🆔 <b>Username:</b> {username}\n\n"
                    f"❌ Aapka message delete kiya gaya kyunki aapne bio mein link lagaya hai.\n"
                    f"🚩 <b>Strikes:</b> {current_strike}/3\n\n"
                    f"<i>Kripya bio link hatayein warna aap mute ho jayenge!</i>"
                )
                warn_msg = await client.send_message(
                    chat_id, 
                    warn_text, 
                    reply_markup=support_buttons()
                )
                
                # Auto-delete warning msg after 10 seconds for clean chat
                await asyncio.sleep(10)
                try:
                    await warn_msg.delete()
                except:
                    pass
            
            else:
                # Step C: Permanent Mute on 3rd strike
                try:
                    await client.restrict_chat_member(
                        chat_id, 
                        user_id, 
                        ChatPermissions(can_send_messages=False)
                    )
                    await client.send_message(
                        chat_id,
                        f"🚫 <b>Muted Forever!</b>\n\n"
                        f"User {message.from_user.mention} ({username}) ko permanently mute kar diya gaya hai. "
                        f"Strike system: Bio mein baar-baar links detect hue.",
                        reply_markup=support_buttons()
                    )
                except Exception as e:
                    print(f"Restriction failed: {e}")
                
                # Strike reset after action
                warning_count[user_id] = 0

    except Exception as e:
        # Ignore errors if bio fetch fails due to user settings
        pass

# --- [WHITELIST COMMANDS] ---
@app.on_message(filters.command("approve") & filters.group)
async def approve_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        approved_users.add(target_user.id)
        
        # User ko unmute kar do agar muted tha toh
        try:
            await client.restrict_chat_member(message.chat.id, target_user.id, ChatPermissions(can_send_messages=True))
        except:
            pass
            
        await message.reply(f"✅ {target_user.mention} ab whitelist hai. Inka bio check nahi hoga.")
    else:
        await message.reply("Kisi ke message par reply karke use approve karein.")

@app.on_message(filters.command("unapprove") & filters.group)
async def unapprove_bio(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id in approved_users:
            approved_users.remove(target_id)
            await message.reply(f"❌ User ko whitelist se hata diya gaya hai.")
