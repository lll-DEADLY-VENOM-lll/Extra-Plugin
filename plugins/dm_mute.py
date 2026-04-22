import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

# Temporary Database
# Real production mein MongoDB use karna behtar hota hai
muted_db = {} 
waiting_for_link = {}

__MODULE__ = "ᴅᴍ ᴍᴜᴛᴇ"
__HELP__ = """
**🛡️ Smart Judge System**

**User (Reporter) ke liye:**
1. Bot ke DM mein screenshot bhejein.
2. Caption mein us bande ki ID ya @username likhen.
3. Bot jab link maange, to group ka link paste karein.
4. Bot usse 4 ghante ke liye mute kar dega.

**Muted User ke liye:**
1. Agar aapko mute kiya gaya hai, to bot ko DM mein apni safai dein.
2. Agar bot ko aapka reason sahi laga (e.g. 'kaam tha', 'sorry'), to wo aapko unmute kar dega.

**Commands:**
• /report - Report karne ka tarika janne ke liye.
"""

# 1. Report Command (Instructions)
@Client.on_message(filters.command("report") & filters.private)
async def report_instruction(client, message):
    await message.reply_text(
        "📝 **Report Kaise Karein?**\n\n"
        "1️⃣ Pehle us spammer ka screenshot lein.\n"
        "2️⃣ Wo photo mujhe bhejein aur **Caption** mein uski ID likhen.\n"
        "3️⃣ Phir main aapse group ka link mangunga.\n\n"
        "Main use 4 ghante ke liye mute kar dunga!"
    )

# 2. Photo Handling (Step 1 of Report)
@Client.on_message(filters.photo & filters.private)
async def handle_report_photo(client, message):
    if not message.caption:
        await message.reply_text("❌ Screenshot ke saath us user ki ID ya @username caption mein likhen!")
        return
    
    offender = message.caption.strip()
    waiting_for_link[message.from_user.id] = {"offender": offender}
    
    await message.reply_text(
        f"✅ Proof mil gaya.\n👤 **Target:** `{offender}`\n\n"
        "Ab us **Group ka Link** bhejiye jahan se wo user aapke DM mein aaya tha."
    )

# 3. Text Handling (Link Verification & Appeal Logic)
@Client.on_message(filters.text & filters.private)
async def handle_private_text(client, message):
    user_id = message.from_user.id
    text = message.text

    # --- Case A: Reporter Group Link de raha hai ---
    if user_id in waiting_for_link:
        offender = waiting_for_link[user_id]["offender"]
        try:
            # Link se username/ID nikalna
            link_raw = text.replace("https://t.me/", "").replace("t.me/", "")
            chat_id = link_raw.split("/")[0]
            
            chat = await client.get_chat(chat_id)
            
            # 4 Ghante ka time calculate karna
            until_time = datetime.now() + timedelta(hours=4)
            
            # Mute Action
            await client.restrict_chat_member(
                chat.id, 
                offender, 
                ChatPermissions(can_send_messages=False),
                until_date=until_time
            )
            
            # Database mein save karna appeal ke liye
            # Offender ki identity (ID ya Username) ko key banayenge
            muted_db[offender] = {"group_id": chat.id, "group_name": chat.title}

            # Group mein alert bhejna
            await client.send_message(
                chat.id,
                f"🚫 **Action:** Muted for 4 Hours\n"
                f"👤 **User:** `{offender}`\n"
                f"🛡️ **Reason:** DM Spam Verified\n"
                f"📝 **Note:** User can DM bot to appeal."
            )
            
            await message.reply_text(f"✅ User `{offender}` ko **{chat.title}** mein 4 ghante ke liye mute kar diya gaya hai.")
            del waiting_for_link[user_id]

        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}\n\nCheck karein ki link sahi hai aur bot group mein admin hai.")
            del waiting_for_link[user_id]
        return

    # --- Case B: Muted User apni safai de raha hai (Appeal Logic) ---
    u_id = str(user_id)
    u_name = f"@{message.from_user.username}" if message.from_user.username else None
    
    # Check if user is in muted list
    offender_key = None
    if u_id in muted_db:
        offender_key = u_id
    elif u_name in muted_db:
        offender_key = u_name

    if offender_key:
        # Bot ka Dimag (Logic)
        # In keywords ka hona aur message ka thoda lamba hona zaroori hai
        keywords = ["sorry", "kaam", "help", "work", "important", "zaroori", "galti", "mistake", "puchna"]
        
        if any(word in text.lower() for word in keywords) and len(text.split()) > 4:
            try:
                target_group = muted_db[offender_key]["group_id"]
                
                # Unmute karna
                await client.restrict_chat_member(
                    target_group, 
                    user_id, 
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
                
                # Group mein batana
                await client.send_message(
                    target_group,
                    f"✅ **Auto-Unmute**\n"
                    f"👤 **User:** {message.from_user.mention}\n"
                    f"🤔 **Bot Decision:** User ki safai sahi lagi. Isliye unmute kar diya gaya."
                )
                
                await message.reply_text("😇 Maine tumhari baat suni aur tumhara reason sahi laga. Maine tumhe group mein unmute kar diya hai. Dobara aisi galti mat karna!")
                del muted_db[offender_key]
                
            except Exception as e:
                print(f"Unmute error: {e}")
        else:
            await message.reply_text(
                "🤨 Ye safai kaafi nahi hai. Thoda detail mein batao ki tumne DM kyun kiya tha? "
                "Mujhe 'sorry' ya 'kaam tha' jaise valid reasons chahiye."
    )
