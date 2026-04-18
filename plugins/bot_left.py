import random
from pyrogram import filters
from pyrogram.types import Message

from config import LOG_GROUP_ID
from VIPMUSIC import app
from VIPMUSIC.utils.database import delete_served_chat, get_assistant
from VIPMUSIC.utils.database import (
    set_loop,
)
from VIPMUSIC.core.call import VIP
from VIPMUSIC.misc import SUDOERS
from VIPMUSIC.core.mongo import mongodb

# Database connection for On/Off system
db = mongodb.leavelog_status

# Photos for logs
photo = [
    "https://telegra.ph/file/1949480f01355b4e87d26.jpg",
    "https://telegra.ph/file/3ef2cc0ad2bc548bafb30.jpg",
    "https://telegra.ph/file/a7d663cd2de689b811729.jpg",
    "https://telegra.ph/file/6f19dc23847f5b005e922.jpg",
    "https://telegra.ph/file/2973150dd62fd27a3a6ba.jpg",
]

# --- On/Off Functions ---
async def is_leavelog_on() -> bool:
    res = await db.find_one({"id": "leavelog"})
    if not res:
        return True  # Default is On
    return res.get("status", True)

async def leavelog_on():
    await db.update_one({"id": "leavelog"}, {"$set": {"status": True}}, upsert=True)

async def leavelog_off():
    await db.update_one({"id": "leavelog"}, {"$set": {"status": False}}, upsert=True)
# -------------------------

@app.on_message(filters.left_chat_member, group=-12)
async def on_left_chat_member(_, message: Message):
    # Check if On/Off system is Enabled
    if not await is_leavelog_on():
        return

    try:
        userbot = await get_assistant(message.chat.id)
        left_chat_member = message.left_chat_member
        
        # Check if the Bot itself is removed/left
        if left_chat_member and left_chat_member.id == (await app.get_me()).id:
            remove_by = (
                message.from_user.mention if message.from_user else "𝐔ɴᴋɴᴏᴡɴ 𝐔sᴇʀ"
            )
            title = message.chat.title
            username = (
                f"@{message.chat.username}" if message.chat.username else "𝐏ʀɪᴠᴀᴛᴇ 𝐂ʜᴀᴛ"
            )
            chat_id = message.chat.id
            
            left = (
                f"✫ <b><u>#𝐋ᴇғᴛ_𝐆ʀᴏᴜᴘ</u></b> ✫\n\n"
                f"<b>𝐂ʜᴀᴛ 𝐓ɪᴛʟᴇ :</b> {title}\n"
                f"<b>𝐂ʜᴀᴛ 𝐈ᴅ :</b> <code>{chat_id}</code>\n"
                f"<b>𝐑ᴇᴍᴏᴠᴇᴅ 𝐁ʏ :</b> {remove_by}\n"
                f"<b>𝐁ᴏᴛ :</b> @{app.username}"
            )
            
            # Send Photo to Log Group
            await app.send_photo(LOG_GROUP_ID, photo=random.choice(photo), caption=left)
            
            # Cleanup Database
            await delete_served_chat(chat_id)
            await VIP.st_stream(chat_id)
            await set_loop(chat_id, 0)
            
            # Assistant leaves the group
            await userbot.leave_chat(chat_id)
            
    except Exception:
        pass

# --- Command to Toggle On/Off (Sudoers/Owner Only) ---
@app.on_message(filters.command(["leavelog", "botleft"]) & SUDOERS)
async def toggle_leavelog(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text("<b>Usage:</b>\n/botleft [on | off]")
    
    state = message.command[1].lower()
    
    if state == "on":
        await leavelog_on()
        await message.reply_text("✅ <b>Bot Left logging system has been enabled.</b>")
    elif state == "off":
        await leavelog_off()
        await message.reply_text("❌ <b>Bot Left logging system has been disabled.</b>")
    else:
        await message.reply_text("<b>Invalid argument!</b> Use `on` or `off`.")

__MODULE__ = "ʙᴏᴛ ʟᴇғᴛ"
__HELP__ = """
<b>/botleft [on/off]</b> - Bot jab group chhodega to uska log aur cleanup system enable ya disable karne ke liye. (Sudoers/Owner Only)
"""
