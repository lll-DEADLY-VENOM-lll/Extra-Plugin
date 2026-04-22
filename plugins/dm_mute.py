import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, Message
from pyrogram.errors import UserNotParticipant, ChatAdminRequired

# Database to store mute records
muted_db = {} 

__MODULE__ = "ᴅᴍ ᴍᴜᴛᴇ"
__HELP__ = """
**Smart Judge Bot (4 Hours Mute)**

1. **Report:** Bot ke DM mein Screenshot bhejein + Caption mein Spammer ki ID.
2. **Link:** Bot aapse Group Link maangega, wo dein.
3. **Action:** Bot usse 4 ghante ke liye mute kar dega aur group mein inform karega.
4. **Appeal:** Muted user bot ko DM karke apni safai de sakta hai.
5. **Brain Logic:** Agar bot ko baat sahi lagi, to wo group mein inform karke turant unmute kar dega.
"""

# --- STEP 1: REPORT & MUTE ---
@Client.on_message(filters.photo & filters.private)
async def report_user(client: Client, message: Message):
    if not message.caption:
        await message.reply_text("❌ Screenshot ke sath us user ki ID ya @username likho.")
        return
    
    offender = message.caption.strip()
    muted_db[message.from_user.id] = {"target": offender, "state": "WANT_LINK"}
    await message.reply_text(f"✅ Proof mil gaya. Ab us Group ka Link do jahan se ye user aaya hai.")

@Client.on_message(filters.text & filters.private)
async def smart_logic(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.lower()

    # --- Reporter Group Link de raha hai ---
    if user_id in muted_db and muted_db[user_id].get("state") == "WANT_LINK":
        link = message.text
        offender = muted_db[user_id]["target"]
        try:
            # Group detect karna
            chat_id = link.replace("https://t.me/", "").split("/")[0]
            chat = await client.get_chat(chat_id)
            
            # 4 Ghante ka Time set karna
            until_date = datetime.now() + timedelta(hours=4)
            
            await client.restrict_chat_member(
                chat.id, 
                offender, 
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            # Data save karna appeal ke liye
            muted_db[offender] = {"group": chat.id, "state": "MUTED", "group_name": chat.title}
            
            # Group mein message bhejna
            await client.send_message(
                chat.id,
                f"🚫 **Action:** Muted for 4 Hours\n"
                f"👤 **User:** `{offender}`\n"
                f"🛡️ **Reason:** DM Spam (Proof Verified)\n"
                f"📝 **Note:** User can DM me to explain his side."
            )
            
            await message.reply_text(f"✅ User ko {chat.title} mein 4 ghante ke liye mute kar diya gaya hai.")
            del muted_db[user_id]
            
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}\nCheck karein ki bot us group mein admin hai.")
        return

    # --- Muted User (Offender) apni safai de raha hai ---
    is_muted = False
    offender_key = None
    
    # User ID ya Username se check karna
    u_id = str(message.from_user.id)
    u_name = f"@{message.from_user.username}" if message.from_user.username else None

    if u_id in muted_db:
        offender_key = u_id
        is_muted = True
    elif u_name and u_name in muted_db:
        offender_key = u_name
        is_muted = True

    if is_muted and muted_db[offender_key]["state"] == "MUTED":
        # Bot ka Logic: Keywords and Length
        valid_keywords = ["kaam", "work", "help", "sorry", "galti", "important", "puchna", "zaroori", "urgency"]
        words = text.split()
        
        if any(word in text for word in valid_keywords) and len(words) > 4:
            try:
                group_id = muted_db[offender_key]["group"]
                group_name = muted_db[offender_key]["group_name"]
                
                # Unmute karna
                await client.restrict_chat_member(
                    group_id, 
                    message.from_user.id, 
                    ChatPermissions(
                        can_send_messages=True, 
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
                
                # Group mein inform karna
                await client.send_message(
                    group_id,
                    f"✅ **Auto-Unmute**\n"
                    f"👤 **User:** {message.from_user.mention}\n"
                    f"🤔 **Bot's Decision:** User ne apni safai di aur wajah sahi lag rahi hai. Isliye unmute kar diya gaya."
                )
                
                await message.reply_text(f"😇 Maine tumhari baat suni aur mujhe laga ki tum sahi ho. Tumhe **{group_name}** mein unmute kar diya gaya hai. Agli baar dhyan rakhna!")
                del muted_db[offender_key]
                
            except Exception as e:
                print(f"Error in unmute: {e}")
        else:
            await message.reply_text(
                "🤨 Ye safai kaafi nahi hai. Thoda detail mein batao ki tumne DM kyun kiya tha? (Kam se kam 5-6 shabd likho)"
  )
