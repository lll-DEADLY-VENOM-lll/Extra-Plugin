import asyncio
from datetime import datetime, timedelta
from pyrogram import filters, enums
from pyrogram.types import ChatPermissions, Message, ChatMemberUpdated
from VIPMUSIC import app  # VIPMUSIC main variable

# --- DATABASE (In-Memory) ---
muted_db = {} 
waiting_for_link = {}
group_settings = {} # {chat_id: True/False}

__MODULE__ = "ᴅᴍ ᴍᴜᴛᴇ"
__HELP__ = """
**🛡️ Smart Judge (Anti-DM Spam System)**

**Admins Ke Liye:**
- `/smartjudge on` : Apne group mein system chalu karein.
- `/smartjudge off` : System band karein.

**Report Karne Ke Liye:**
- `/report` : Group mein likhein ya Bot ke DM mein guide dekhein.
- Screenshot bot ko DM karein aur Caption mein spammer ki ID likhein.
"""

# --- 1. ADMIN UNMUTE DETECTOR ---
@app.on_chat_member_updated()
async def respect_admin_decision(client, update: ChatMemberUpdated):
    if not update.new_chat_member:
        return
    
    chat_id = update.chat.id
    user_id = update.new_chat_member.user.id
    status = update.new_chat_member.status
    
    if status == enums.ChatMemberStatus.MEMBER:
        if update.new_chat_member.permissions and update.new_chat_member.permissions.can_send_messages:
            u_id = str(user_id)
            if u_id in muted_db and muted_db[u_id]["chat_id"] == chat_id:
                del muted_db[u_id]

# --- 2. ON/OFF COMMAND ---
@app.on_message(filters.command("smartjudge") & filters.group)
async def toggle_smartjudge(client, message: Message):
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
        return await message.reply_text("❌ Sirf Admins hi ise use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text("Sahi tareeka: `/smartjudge on` ya `/smartjudge off`")

    choice = message.command[1].lower()
    if choice == "on":
        group_settings[message.chat.id] = True
        await message.reply_text("✅ SmartJudge System ON.")
    elif choice == "off":
        group_settings[message.chat.id] = False
        await message.reply_text("📴 SmartJudge System OFF.")

# --- 3. REPORT COMMAND ---
@app.on_message(filters.command("report"))
async def report_command(client, message: Message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not group_settings.get(message.chat.id, False):
            return await message.reply_text("⚠️ Is group mein system band hai.")
        
        await message.reply_text(
            "📝 **Report Guide:**\n"
            "1. Spammer ka screenshot lein.\n"
            f"2. Bot (@{(await client.get_me()).username}) ke DM mein photo bhejein.\n"
            "3. Caption mein user ki ID likhein."
        )
    else:
        await message.reply_text("Spammer ka screenshot bhejo aur Caption mein uski ID likho.")

# --- 4. CAPTURE PHOTO (Private Only) ---
@app.on_message(filters.photo & filters.private)
async def catch_photo(_, message):
    if not message.caption:
        return await message.reply_text("❌ Caption mein Spammer ki ID likhein!")
    
    waiting_for_link[message.from_user.id] = message.caption.strip()
    await message.reply_text("✅ Proof mil gaya. Ab us **Group ki ID (-100xxx)** bhejiye.")

# --- 5. PRIVATE TEXT HANDLER (Logic & Appeal) ---
# FIX: Added parentheses to filters.command and a list of commands to exclude
@app.on_message(filters.private & filters.text & ~filters.command(["start", "help", "report", "smartjudge"]))
async def handle_private_logic(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    # --- A. Reporting Process ---
    if user_id in waiting_for_link:
        offender = waiting_for_link[user_id]
        if not text.startswith("-100"):
            return await message.reply_text("❌ Galat Group ID! ID -100 se shuru hoti hai.")
        
        try:
            chat_id = int(text)
            if not group_settings.get(chat_id, False):
                del waiting_for_link[user_id]
                return await message.reply_text("❌ Is group mein system OFF hai.")

            # Mute Action
            until_date = datetime.now() + timedelta(hours=4)
            await client.restrict_chat_member(chat_id, offender, ChatPermissions(can_send_messages=False), until_date=until_date)
            
            muted_db[str(offender)] = {"chat_id": chat_id}
            await client.send_message(chat_id, f"🚫 **Action:** Muted\n👤 **User:** `{offender}`\n🛡️ **Reason:** DM Proof Verified")
            await message.reply_text(f"✅ User `{offender}` ko mute kar diya gaya hai.")
            del waiting_for_link[user_id]
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")
            if user_id in waiting_for_link: del waiting_for_link[user_id]
        return

    # --- B. Appeal Logic ---
    u_id = str(user_id)
    if u_id in muted_db:
        keywords = ["sorry", "galti", "maaf", "help", "work", "important", "zaroori", "puchna", "unmute"]
        
        if any(w in text.lower() for w in keywords) and len(text.split()) >= 4:
            try:
                target_chat = muted_db[u_id]["chat_id"]
                await client.restrict_chat_member(target_chat, user_id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
                await client.send_message(target_chat, f"✅ **Auto-Unmute**\n👤 **User:** {message.from_user.mention}\nSafai manzoor ki gayi.")
                await message.reply_text("😇 Tumhe unmute kar diya gaya hai. Spam mat karna!")
                del muted_db[u_id]
            except: pass
        else:
            await message.reply_text("🤨 Safai sahi nahi hai. Kam se kam 5 words mein explain karo kyun DM kiya? Ya phir wait karo.")
