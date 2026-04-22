import asyncio
import random
from pyrogram import filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import RPCError
from VIPMUSIC import app

# --- MODULE SETTINGS ---
__MODULE__ = "ᴜsᴇʀ ʟᴇғᴛ"
__HELP__ = """
**User Left Settings:**

/userleft [on/off] - Group se jane wale members ka notification on ya off karein.

**Note:** 
- Ye command sirf Admins ke liye hai.
- Leave message 30 seconds baad apne aap delete ho jayega.
"""

# Dictionary to store status per chat
LEAVE_STATE = {}

# --- COMMAND TO ENABLE/DISABLE ---
@app.on_message(filters.command("userleft") & filters.group)
async def toggle_leave_log(client, message: Message):
    # Check if the sender is an admin
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if not member.privileges:
        return await message.reply_text("❌ **Arre Bhaiya! Sirf admins hi isse on/off kar sakte hain.**")

    if len(message.command) < 2:
        return await message.reply_text("✨ **Usage:** `/userleft on` or `/userleft off`")

    input_state = message.command[1].lower()
    
    if input_state == "on":
        LEAVE_STATE[message.chat.id] = True
        await message.reply_text("✅ **User Left notification on ho gaya hai, Bhaiya!**")
    elif input_state == "off":
        LEAVE_STATE[message.chat.id] = False
        await message.reply_text("❌ **User Left notification band kar diya gaya hai.**")
    else:
        await message.reply_text("Invalid! `/userleft on` ya `off` likhein.")

# --- EVENT HANDLER (When someone leaves) ---
@app.on_chat_member_updated(filters.group, group=-7)
async def member_has_left(client: app, member: ChatMemberUpdated):
    # Check if setting is ON for this chat
    if not LEAVE_STATE.get(member.chat.id, False):
        return

    # Detection logic for leaving
    if (
        not member.new_chat_member
        and member.old_chat_member 
        and member.old_chat_member.status not in {"banned", "left", "restricted"}
    ):
        user = member.old_chat_member.user if member.old_chat_member else member.from_user
        
        # --- STYLISH "BHAIYA" TEXT ---
        leave_text = (
            f"<b>┏━⦿ 『 ᴜsᴇʀ ʟᴇғᴛ ʙʜᴀɪʏᴀ 』</b>\n"
            f"<b>┠╼╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╼</b>\n"
            f"<b>┃</b>\n"
            f"<b>┃ 👤 ɴᴀᴍᴇ :</b> {user.mention}\n"
            f"<b>┃ 🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>┃ 🥀 sᴛᴀᴛᴜs :</b> <b>ɢʀᴏᴜᴘ sᴇ ᴄʜᴀʟᴇ ɢᴀʏᴇ</b>\n"
            f"<b>┃</b>\n"
            f"<b>┗━⦿ ʙʏᴇ ʙʏᴇ ʙʜᴀɪʏᴀ 👋 ᴛᴀᴛᴀ !</b>"
        )
        
        try:
            msg = await client.send_message(
                chat_id=member.chat.id,
                text=leave_text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("✨ ᴠɪᴇᴡ ʙʜᴀɪʏᴀ ᴘʀᴏғɪʟᴇ ✨", user_id=user.id)]]
                ),
            )

            # Auto-delete after 30 seconds
            async def delete_after_delay():
                await asyncio.sleep(30)
                try:
                    await msg.delete()
                except:
                    pass

            asyncio.create_task(delete_after_delay())

        except Exception as e:
            print(f"Error: {e}")
