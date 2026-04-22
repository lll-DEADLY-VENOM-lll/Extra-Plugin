import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import ChatPermissions
from VIPMUSIC import app  # VIPMUSIC ka main bot variable

# Database (Temporary)
# Note: Bot restart hone par ye data reset ho jayega
muted_db = {} 
waiting_for_link = {}

__MODULE__ = "ᴅᴍ ᴍᴜᴛᴇ"
__HELP__ = """
**🛡️ Smart Judge System (Anti-DM Spam)**

**1. Report Kaise Karein?**
- Bot ke DM mein screenshot bhejein.
- Caption mein Spammer ki ID ya @Username likhen.
- Bot jab puche, to Group ka Link bhej dein.
- Bot 4 ghante ke liye usse mute kar dega.

**2. Unmute Kaise Karein?**
- Muted user bot ko DM karein.
- Agar user 'sorry', 'kaam tha', ya 'important' bolta hai (min 5 words), 
  to bot use automatic unmute kar dega.

**Command:**
/report - Report karne ka tarika janne ke liye.
"""

# --- INSTRUCTIONS ---
@app.on_message(filters.command("report") & filters.private)
async def report_help(_, message):
    await message.reply_text(
        "📝 **Report Karne Ka Tarika:**\n\n"
        "1️⃣ Spammer ka screenshot lein.\n"
        "2️⃣ Photo mujhe bhejein aur **Caption** mein uski ID likhen.\n"
        "3️⃣ Phir main aapse group ka link mangunga jahan se wo aaya hai.\n\n"
        "Main turant action lunga!"
    )

# --- STEP 1: PHOTO & ID RECEIVE KARNA ---
@app.on_message(filters.photo & filters.private)
async def report_photo_step(_, message):
    if not message.caption:
        await message.reply_text("❌ Screenshot ke sath Spammer ka ID ya @username caption mein likho!")
        return
    
    target_id = message.caption.strip()
    # Reporter ki ID save karna taaki agla link usise liya jaye
    waiting_for_link[message.from_user.id] = target_id
    
    await message.reply_text(
        f"✅ Proof mil gaya.\n👤 **Target:** `{target_id}`\n\n"
        "Ab us **Group ka Link** (t.me/link) bhejiye jahan ye spammer hai."
    )

# --- STEP 2: LINK RECEIVE KARNA & MUTE KARNA ---
@app.on_message(filters.text & filters.private)
async def handle_dm_logic(client, message):
    user_id = message.from_user.id
    text = message.text

    # Link mangne ka logic (For Reporter)
    if user_id in waiting_for_link:
        offender = waiting_for_link[user_id]
        try:
            # Link se ID nikalna
            chat_id_raw = text.replace("https://t.me/", "").replace("t.me/", "").split("/")[0]
            chat = await client.get_chat(chat_id_raw)
            
            # 4 Ghante ka time calculate karna
            until_date = datetime.now() + timedelta(hours=4)
            
            # Action: Mute
            await client.restrict_chat_member(
                chat.id, 
                offender, 
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            # Appeal ke liye record save karna
            muted_db[str(offender)] = {"chat_id": chat.id, "chat_title": chat.title}
            
            # Group mein message
            await client.send_message(
                chat.id, 
                f"🚫 **Action:** Muted (4 Hours)\n"
                f"👤 **User:** `{offender}`\n"
                f"🛡️ **Reason:** DM Proof Verified via Bot\n\n"
                f"📝 _User DM mein apni safai de sakta hai unmute hone ke liye._"
            )
            
            await message.reply_text(f"✅ User `{offender}` ko {chat.title} mein mute kar diya gaya hai.")
            del waiting_for_link[user_id]
            
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}\n\nCheck karein ki Link sahi hai aur bot group mein admin hai.")
            del waiting_for_link[user_id]
        return

    # --- APPEAL LOGIC (Muted user ke liye) ---
    u_id = str(user_id)
    u_name = f"@{message.from_user.username}" if message.from_user.username else "NONE"

    # Check agar user muted list mein hai
    offender_key = None
    if u_id in muted_db: offender_key = u_id
    elif u_name in muted_db: offender_key = u_name

    if offender_key:
        # Bot ka Dimag (Logic)
        keywords = ["sorry", "kaam", "help", "work", "important", "zaroori", "galti", "mistake", "puchna"]
        
        # Logic: Kam se kam 5 words aur 1 keyword hona chahiye
        if any(word in text.lower() for word in keywords) and len(text.split()) >= 4:
            try:
                target_chat_id = muted_db[offender_key]["chat_id"]
                
                # Unmute Action
                await client.restrict_chat_member(
                    target_chat_id, 
                    user_id, 
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
                
                # Group Notification
                await client.send_message(
                    target_chat_id, 
                    f"✅ **Auto-Unmute**\n"
                    f"👤 **User:** {message.from_user.mention}\n"
                    f"🤔 **Reason:** User ne apni safai di aur bot ko wajah sahi lagi."
                )
                
                await message.reply_text("😇 Maine tumhari baat suni aur mujhe laga ki tumhara maqsad bura nahi tha. Tumhe unmute kar diya gaya hai. Agli baar dhyan rakhna!")
                del muted_db[offender_key]
                
            except Exception as e:
                print(f"Unmute Error: {e}")
        else:
            await message.reply_text(
                "🤨 Ye safai kaafi nahi hai. Thoda detail mein batao ki tumne DM kyun kiya tha?\n"
                "Kam se kam 5 words likho aur 'sorry' ya 'kaam tha' jaisi valid baat kaho."
            )
