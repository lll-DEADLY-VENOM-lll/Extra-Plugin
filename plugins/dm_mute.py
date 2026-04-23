import asyncio
from datetime import datetime, timedelta
from pyrogram import filters, enums
from pyrogram.types import ChatPermissions, Message, ChatMemberUpdated
from VIPMUSIC import app  # VIPMUSIC main variable

# --- DATABASE (In-Memory) ---
muted_db = {} 
waiting_for_group = {}    # {user_id: offender_id}
group_settings = {}       # {chat_id: True/False}
authorized_to_report = {} # {user_id: True} -> Isse bot DM mein active hota hai

__MODULE__ = "ᴅᴍ ʀᴇᴘᴏʀᴛ"
__HELP__ = """
🛡️ **sᴍᴀʀᴛ ᴊᴜᴅɢᴇ (ᴀɴᴛɪ-ᴅᴍ sᴘᴀᴍ)**

**ᴀᴅᴍɪɴs ᴄᴏᴍᴍᴀɴᴅs:**
- `/smartjudge on` : ɢʀᴏᴜᴘ ᴍᴇɪɴ sʏsᴛᴇᴍ ᴄʜᴀʟᴜ ᴋᴀʀᴇɪɴ.
- `/smartjudge off` : sʏsᴛᴇᴍ ʙᴀɴᴅ ᴋᴀʀᴇɪɴ.

**ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs:**
- `/report` : ᴅᴍ sᴘᴀᴍᴍᴇʀ ᴋɪ ʀᴇᴘᴏʀᴛ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ (ɢʀᴏᴜᴘ ᴍᴇɪɴ ʟɪᴋʜᴇɪɴ).

**ʀᴇᴘᴏʀᴛ ᴘʀᴏᴄᴇss:**
1. ɢʀᴏᴜᴘ ᴍᴇɪɴ `/report` ʟɪᴋʜᴇɪɴ.
2. ʙᴏᴛ ᴋᴇ ᴅᴍ ᴍᴇɪɴ sᴄʀᴇᴇɴsʜᴏᴛ ʙʜᴇᴊᴇɪɴ.
3. ᴄᴀᴘᴛɪᴏɴ ᴍᴇɪɴ sᴘᴀᴍᴍᴇʀ ᴋɪ ɪᴅ ʟɪᴋʜᴇɪɴ.
4. ʙᴏᴛ ᴋᴏ ɢʀᴏᴜᴘ ɪᴅ ʙʜᴇᴊᴇɪɴ ᴊᴀʜᴀɴ sᴘᴀᴍᴍᴇʀ ᴍᴀᴜᴊᴏᴏᴅ ʜᴀɪ.

**ɴᴏᴛᴇ:** ʙᴏᴛ ᴅᴍ ᴍᴇɪɴ ᴛᴀʙʜɪ ᴊᴀᴡᴀʙ ᴅᴇɢᴀ ᴊᴀʙ ᴀᴀᴘ ɢʀᴏᴜᴘ ᴍᴇɪɴ `/report` ᴋᴀʀᴇɪɴɢᴇ.
"""

# --- 1. ADMIN UNMUTE DETECTOR ---
@app.on_chat_member_updated()
async def respect_admin_decision(client, update: ChatMemberUpdated):
    if not update.new_chat_member:
        return
    chat_id = update.chat.id
    user_id = update.new_chat_member.user.id
    if update.new_chat_member.status == enums.ChatMemberStatus.MEMBER:
        if update.new_chat_member.permissions and update.new_chat_member.permissions.can_send_messages:
            u_id = str(user_id)
            if u_id in muted_db and muted_db[u_id]["chat_id"] == chat_id:
                del muted_db[u_id]

# --- 2. TOGGLE SYSTEM ---
@app.on_message(filters.command("smartjudge") & filters.group)
async def toggle_smartjudge(client, message: Message):
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
        return await message.reply_text("❌ Sirf Admins hi use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text("Sahi tareeka: `/smartjudge on` or `off`")

    choice = message.command[1].lower()
    group_settings[message.chat.id] = (choice == "on")
    await message.reply_text(f"✅ SmartJudge System **{choice.upper()}**")

# --- 3. REPORT TRIGGER ---
@app.on_message(filters.command("report") & filters.group)
async def report_command(client, message: Message):
    if not group_settings.get(message.chat.id, False):
        return await message.reply_text("⚠️ System OFF hai. Admin ko kahein `/smartjudge on` karein.")

    authorized_to_report[message.from_user.id] = True
    bot_username = (await client.get_me()).username
    await message.reply_text(
        f"✅ {message.from_user.mention}, Report permission granted!\n\n"
        f"1. Bot (@{bot_username}) ke **DM mein jayein**.\n"
        f"2. Screenshot ke Caption mein **Spammer ID** likh kar bhejein.\n"
        f"3. Bot aapse is Group ki ID mangega: `{message.chat.id}`"
    )

# --- 4. PRIVATE MESSAGE LOGIC (Silent Mode) ---
@app.on_message(filters.private)
async def handle_private_messages(client, message: Message):
    user_id = message.from_user.id
    u_id_str = str(user_id)

    # Authorization Check
    is_authorized = authorized_to_report.get(user_id, False)
    is_muted = u_id_str in muted_db

    # AGAR AUTHORIZED NAHI HAI TO BOT KUCH NAHI BOLEGA
    if not is_authorized and not is_muted:
        return

    # A. Reporting Flow
    if is_authorized:
        if message.photo:
            if not message.caption:
                return await message.reply_text("❌ Caption mein Spammer ki ID likho!")
            
            waiting_for_group[user_id] = message.caption.strip()
            await message.reply_text("✅ Proof received! Ab **Group ID** (-100xxx) bhejiye.")
            return

        if message.text and user_id in waiting_for_group:
            group_id_text = message.text.strip()
            if not group_id_text.startswith("-100"):
                return await message.reply_text("❌ Galat Group ID. ID `-100` se shuru hoti hai.")
            
            try:
                chat_id = int(group_id_text)
                offender = waiting_for_group[user_id]

                if not group_settings.get(chat_id, False):
                    del authorized_to_report[user_id]
                    del waiting_for_group[user_id]
                    return await message.reply_text("❌ Is group mein system ON nahi hai.")

                # Restrict Member
                until_date = datetime.now() + timedelta(hours=4)
                await client.restrict_chat_member(chat_id, offender, ChatPermissions(can_send_messages=False), until_date=until_date)
                
                muted_db[str(offender)] = {"chat_id": chat_id}
                await client.send_message(chat_id, f"🚫 **Muted:** `{offender}`\n🛡️ **Reason:** DM Spam Verified")
                await message.reply_text("✅ User ko mute kar diya gaya hai.")
                
                # Reset
                del authorized_to_report[user_id]
                del waiting_for_group[user_id]
                return
            except Exception as e:
                await message.reply_text(f"❌ Error: {e}")
                return

    # B. Appeal Flow
    if is_muted and message.text:
        text = message.text.lower()
        keywords = ["sorry", "galti", "maaf", "puchna", "zaroori", "help"]
        if any(w in text for w in keywords) and len(text.split()) >= 4:
            try:
                target_chat = muted_db[u_id_str]["chat_id"]
                await client.restrict_chat_member(target_chat, user_id, ChatPermissions(can_send_messages=True, can_send_media_messages=True))
                await client.send_message(target_chat, f"✅ **Unmuted:** {message.from_user.mention} ne mafi maangi.")
                await message.reply_text("😇 Theek hai, unmute kar diya. Dobara mat karna!")
                del muted_db[u_id_str]
            except: pass
        else:
            await message.reply_text("🤨 Safai sahi nahi hai, dhang se explain karo.")
