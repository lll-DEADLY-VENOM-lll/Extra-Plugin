import asyncio
from datetime import datetime, timedelta
from pyrogram import filters, enums
from pyrogram.types import ChatPermissions, Message, ChatMemberUpdated
from VIPMUSIC import app  # VIPMUSIC main variable

# --- DATABASE (In-Memory) ---
# Note: Bot restart hone par data clear ho jayega. 
muted_db = {} 
waiting_for_group = {}    # {user_id: offender_id}
group_settings = {}       # {chat_id: True/False}
authorized_to_report = {} # {user_id: True} -> Silent mode bypass

MODULE = "ᴅᴍ ᴍᴜᴛᴇ"
HELP = """ 🛡️ Smart Judge (Anti-DM Spam System)

Admins Ke Liye:
  - /smartjudge on : System chalu karein.
  - /smartjudge off : System band karein.

Report Kaise Karein:
  1. Group mein /report likhein (Isse bot DM mein aapse baat karega).
  2. Bot ke DM mein Screenshot bhejein.
  3. Caption mein Spammer ki ID likhein.
  4. Bot ko Group ID bhejein.
"""

# --- 1. ADMIN UNMUTE DETECTOR ---
# Agar admin manually kisi ko unmute kare, to bot record clear kar dega
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

# --- 2. SMARTJUDGE ON/OFF (Only for Group Admins) ---
@app.on_message(filters.command("smartjudge") & filters.group)
async def toggle_smartjudge(client, message: Message):
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
        return await message.reply_text("❌ Sirf Admins hi SmartJudge control kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text("Sahi tareeka: `/smartjudge on` ya `/smartjudge off`")

    choice = message.command[1].lower()
    if choice == "on":
        group_settings[message.chat.id] = True
        await message.reply_text("✅ **SmartJudge System ON.** Ab /report command kaam karegi.")
    elif choice == "off":
        group_settings[message.chat.id] = False
        await message.reply_text("📴 **SmartJudge System OFF.**")
    else:
        await message.reply_text("Sahi tareeka: `on` ya `off`.")

# --- 3. REPORT COMMAND (Activation Trigger) ---
@app.on_message(filters.command("report") & filters.group)
async def report_command(client, message: Message):
    # Check if system is ON in this group
    if not group_settings.get(message.chat.id, False):
        return await message.reply_text("⚠️ Is group mein `/report` system band hai. Admin ko kahein `/smartjudge on` karein.")

    # User ko allow karna DM mein report ke liye
    authorized_to_report[message.from_user.id] = True
    
    bot_username = (await client.get_me()).username
    await message.reply_text(
        f"✅ {message.from_user.mention}, aapko report karne ki permission mil gayi hai.\n\n"
        f"📝 **Ab ye steps follow karein:**\n"
        f"1️⃣ Bot (@{bot_username}) ke **DM mein jayein**.\n"
        f"2️⃣ Spammer ke chat ka **Screenshot** bhejien.\n"
        f"3️⃣ Photo ke **Caption** mein spammer ki ID likhein.\n"
        f"4️⃣ Main aapse Group ID maangunga, ye bhej dena: `{message.chat.id}`"
    )

# --- 4. PRIVATE MESSAGE HANDLER (Report & Appeal Logic) ---
@app.on_message(filters.private)
async def handle_private_messages(client, message: Message):
    user_id = message.from_user.id
    u_id_str = str(user_id)

    # 1. Check if user is authorized to report OR is a muted user trying to appeal
    is_authorized = authorized_to_report.get(user_id, False)
    is_muted = u_id_str in muted_db

    # AGAR DONO NAHI HAI TO BOT BILKUL KUCH NAHI BOLEGA (SILENT)
    if not is_authorized and not is_muted:
        return

    # --- CASE A: REPORTING PROCESS ---
    if is_authorized:
        # Step 1: Capture Photo and Offender ID
        if message.photo:
            if not message.caption:
                return await message.reply_text("❌ Screenshot ke sath Caption mein Spammer ki ID ya Username likhein!")
            
            waiting_for_group[user_id] = message.caption.strip()
            await message.reply_text(
                "✅ Proof mil gaya.\n\n"
                "Ab us **Group ki ID (-100xxx)** bhejiye jahan se wo spammer aaya hai."
            )
            return

        # Step 2: Capture Group ID and Take Action
        if message.text and user_id in waiting_for_group:
            group_id_text = message.text.strip()
            
            if not group_id_text.startswith("-100"):
                return await message.reply_text("❌ Galat Group ID! ID hamesha `-100` se shuru hoti hai.")
            
            try:
                chat_id = int(group_id_text)
                offender = waiting_for_group[user_id]

                # Check if SmartJudge is ON in that group
                if not group_settings.get(chat_id, False):
                    del authorized_to_report[user_id]
                    del waiting_for_group[user_id]
                    return await message.reply_text("❌ Is group mein SmartJudge ON nahi hai. Action cancel.")

                # Admin Immunity check
                try:
                    member = await client.get_chat_member(chat_id, offender)
                    if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                        del authorized_to_report[user_id]
                        del waiting_for_group[user_id]
                        return await message.reply_text("❌ Woh user ek Admin hai, main use mute nahi kar sakta.")
                except: pass

                # Perform Mute (4 Hours)
                until_date = datetime.now() + timedelta(hours=4)
                await client.restrict_chat_member(
                    chat_id, 
                    offender, 
                    ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                
                muted_db[str(offender)] = {"chat_id": chat_id}
                
                await client.send_message(
                    chat_id, 
                    f"🚫 **Action:** Muted (4 Hours)\n"
                    f"👤 **User:** `{offender}`\n"
                    f"🛡️ **Reason:** DM Proof Verified by {message.from_user.mention}"
                )
                
                await message.reply_text(f"✅ User `{offender}` ko mute kar diya gaya hai.")
                
                # Cleanup: authorization khatam
                del authorized_to_report[user_id]
                del waiting_for_group[user_id]
                return

            except Exception as e:
                await message.reply_text(f"❌ Error: `{e}`")
                del authorized_to_report[user_id]
                del waiting_for_group[user_id]
                return

    # --- CASE B: APPEAL LOGIC (For Muted Users) ---
    if is_muted and message.text:
        text = message.text.lower()
        keywords = ["sorry", "galti", "maaf", "help", "work", "important", "zaroori", "puchna"]
        
        if any(w in text for w in keywords) and len(text.split()) >= 4:
            try:
                target_chat = muted_db[u_id_str]["chat_id"]
                
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
                del muted_db[u_id_str]
            except Exception:
                pass
        else:
            await message.reply_text("🤨 Safai sahi nahi hai. Kam se kam 4-5 words mein explain karo kyun DM kiya?")
