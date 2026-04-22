import asyncio
from datetime import datetime, timedelta
from pyrogram import filters, enums
from pyrogram.types import ChatPermissions, Message, ChatMemberUpdated
from VIPMUSIC import app  # VIPMUSIC main variable

# --- DATABASE (In-Memory) ---
# Note: Bot restart hone par data clear ho jayega. 
# Permanent database ke liye ise MongoDB/SQL se connect karna hoga.
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

**Special Features:**
- Admin ne kisi ko unmute kiya, to bot interfere nahi karega.
- Admin ko mute nahi kiya ja sakta.
- Muted user bot ko DM mein safai dekar unmute ho sakta hai.
"""

# --- 1. ADMIN UNMUTE DETECTOR ---
# Agar admin kisi user ko manually settings se unmute karega, 
# to bot record se us user ko hata dega.
@app.on_chat_member_updated()
async def respect_admin_decision(client, update: ChatMemberUpdated):
    if not update.new_chat_member:
        return
    
    chat_id = update.chat.id
    user_id = update.new_chat_member.user.id
    status = update.new_chat_member.status
    
    # Check agar user "Member" hai aur uske paas message bhejne ki permission hai
    if status == enums.ChatMemberStatus.MEMBER:
        if update.new_chat_member.permissions and update.new_chat_member.permissions.can_send_messages:
            u_id = str(user_id)
            if u_id in muted_db and muted_db[u_id]["chat_id"] == chat_id:
                del muted_db[u_id]
                print(f"DEBUG: Admin ne {user_id} ko manually unmute kiya.")

# --- 2. ON/OFF COMMAND (Admin Only) ---
@app.on_message(filters.command("smartjudge") & filters.group)
async def toggle_smartjudge(client, message: Message):
    # Check if sender is admin
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
        return await message.reply_text("❌ Maaf kijiye, sirf Admins hi SmartJudge control kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text("Sahi tareeka: `/smartjudge on` ya `/smartjudge off`")

    choice = message.command[1].lower()
    if choice == "on":
        group_settings[message.chat.id] = True
        await message.reply_text("✅ **SmartJudge System ON.** Ab is group ke liye DM reports accept ki jayengi.")
    elif choice == "off":
        group_settings[message.chat.id] = False
        await message.reply_text("📴 **SmartJudge System OFF.** Ab koi report process nahi hogi.")
    else:
        await message.reply_text("Invalid Option. Use `on` or `off`.")

# --- 3. REPORT COMMAND (Respecting ON/OFF) ---
@app.on_message(filters.command("report"))
async def report_command(client, message: Message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        # Check if ON in this group
        if not group_settings.get(message.chat.id, False):
            return await message.reply_text("⚠️ Is group mein `/report` system band hai. Admin ko kahein `/smartjudge on` karein.")
        
        await message.reply_text(
            "📝 **DM Spam Report Kaise Karein?**\n\n"
            "1️⃣ Spammer ke chat ka screenshot lein.\n"
            "2️⃣ Bot ke DM (@" + (await client.get_me()).username + ") mein photo bhejein.\n"
            "3️⃣ **Caption** mein us user ki ID ya Username likhein.\n"
            f"4️⃣ Group ID maange to ye bhejien: `{message.chat.id}`"
        )
    else:
        # Private message report guide
        await message.reply_text(
            "📝 **Report Guide:**\n"
            "Spammer ka screenshot bhejo aur Caption mein uski ID likho. "
            "Phir main aapse us Group ki ID mangunga jahan se wo aaya hai."
        )

# --- 4. STEP 1: CAPTURE PHOTO (Private Only) ---
@app.on_message(filters.photo & filters.private)
async def catch_photo(_, message):
    if not message.caption:
        return await message.reply_text("❌ Screenshot ke sath caption mein Spammer ki ID ya Username likhein!")
    
    waiting_for_link[message.from_user.id] = message.caption.strip()
    await message.reply_text(
        "✅ Proof mil gaya.\n\n"
        "Ab us **Group ki ID (-100xxx)** bhejiye jahan se wo spammer aaya hai.\n"
        "**Note:** Us group mein SmartJudge ON hona chahiye."
    )

# --- 5. STEP 2: LOGIC & MUTE ACTION (Private Only) ---
@app.on_message(filters.text & filters.private)
async def handle_private_logic(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Reporting Process logic
    if user_id in waiting_for_link:
        offender = waiting_for_link[user_id]
        try:
            # Group ID verification
            if not text.startswith("-100"):
                return await message.reply_text("❌ Galat Group ID! ID hamesha `-100` se shuru hoti hai.")
            
            chat_id = int(text)

            # Check if group has system ON
            if not group_settings.get(chat_id, False):
                del waiting_for_link[user_id]
                return await message.reply_text("❌ Is group ke Admin ne `/report` system ko OFF rakha hai. Action nahi liya ja sakta.")

            # Admin Immunity check
            try:
                member = await client.get_chat_member(chat_id, offender)
                if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                    del waiting_for_link[user_id]
                    return await message.reply_text("❌ Woh user ek Admin hai, main use mute nahi kar sakta.")
            except: pass # User group mein nahi hai ya ID galat hai

            # Perform Mute (4 Hours)
            until_date = datetime.now() + timedelta(hours=4)
            await client.restrict_chat_member(
                chat_id, 
                offender, 
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            # Save for Appeal handling
            muted_db[str(offender)] = {"chat_id": chat_id}
            
            await client.send_message(
                chat_id, 
                f"🚫 **Action:** Muted (4 Hours)\n"
                f"👤 **User:** `{offender}`\n"
                f"🛡️ **Reason:** DM Proof Verified\n"
                f"📝 **Note:** Admin chahein to manually unmute kar sakte hain."
            )
            
            await message.reply_text(f"✅ User `{offender}` ko mute kar diya gaya hai.")
            del waiting_for_link[user_id]

        except Exception as e:
            await message.reply_text(f"❌ Error: `{e}`\nCheck karein ki bot group mein admin hai.")
            if user_id in waiting_for_link: del waiting_for_link[user_id]
        return

    # --- 6. APPEAL LOGIC (Muted user ke liye) ---
    u_id = str(user_id)
    if u_id in muted_db:
        # Keywords based logic for auto-unmute
        keywords = ["sorry", "galti", "maaf", "help", "work", "important", "zaroori", "puchna"]
        
        if any(w in text.lower() for w in keywords) and len(text.split()) >= 4:
            try:
                target_chat = muted_db[u_id]["chat_id"]
                
                # Unmute
                await client.restrict_chat_member(
                    target_chat, 
                    user_id, 
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
                
                await client.send_message(
                    target_chat, 
                    f"✅ **Auto-Unmute**\n👤 **User:** {message.from_user.mention}\n"
                    f"🤔 **Faisla:** User ne bot ko valid safai di."
                )
                
                await message.reply_text("😇 Maine tumhari safai suni aur tumhe unmute kar diya hai. Dobara spam mat karna!")
                del muted_db[u_id]
            except Exception:
                pass
        else:
            await message.reply_text("🤨 Safai sahi nahi hai. Kam se kam 5 words mein explain karo kyun DM kiya?")
