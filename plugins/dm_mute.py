import asyncio
import re
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import ChatPermissions
from VIPMUSIC import app  # VIPMUSIC framework ka main variable

# Temporary Database (In-Memory)
# Note: Bot restart hone par ye memory clear ho jayegi
muted_db = {} 
waiting_for_link = {}

__MODULE__ = "SmartJudge"
__HELP__ = """
**🛡️ Smart Judge (Anti-DM Spam System)**

**Report Kaise Karein?**
1. Spammer ka screenshot lein.
2. Photo bot ko bhejein aur **Caption** mein uski ID ya Username likhen.
3. Bot link maange to Group ka Link ya Group ID (-100xxx) bhej dein.
4. Bot 4 ghante ke liye mute kar dega.

**Unmute (Appeal) Kaise Karein?**
- Muted user bot ko DM mein message kare (e.g., 'Sorry, kaam tha').
- Bot logic use karke khud faisla lega aur unmute kar dega.

**Commands:**
/report - Guide dekhne ke liye.
"""

# --- INSTRUCTIONS ---
@app.on_message(filters.command("report") & filters.private)
async def report_guide(_, message):
    await message.reply_text(
        "📝 **Report Karne Ki Vidhi:**\n\n"
        "1️⃣ Pehle spammer ka screenshot lein.\n"
        "2️⃣ Wo photo mujhe bhejein aur **Caption** mein uski ID likhen.\n"
        "3️⃣ Phir main aapse group ka link mangunga.\n\n"
        "⚠️ **Note:** Agar group private hai, to uska Link ki jagah ID bhej sakte hain."
    )

# --- STEP 1: PHOTO & ID CAPTURE ---
@app.on_message(filters.photo & filters.private)
async def catch_photo(_, message):
    if not message.caption:
        await message.reply_text("❌ Photo ke sath Spammer ka ID ya Username caption mein likho!")
        return
    
    offender_id = message.caption.strip()
    # Reporter ki ID ko key bana kar offender ko save karna
    waiting_for_link[message.from_user.id] = offender_id
    
    await message.reply_text(
        f"✅ Proof mil gaya.\n👤 **Target:** `{offender_id}`\n\n"
        "Ab us **Group ka Link** ya **ID (-100xxx)** bhejiye jahan se wo user aaya hai."
    )

# --- STEP 2: LINK PROCESSING & MUTE ACTION ---
@app.on_message(filters.text & filters.private)
async def handle_logic(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Agar ye message kisi report ke process mein hai
    if user_id in waiting_for_link:
        offender = waiting_for_link[user_id]
        
        # Link se Chat ID nikalne ka logic
        chat_id = None
        if text.startswith("-100") or text.isdigit():
            chat_id = int(text)
        elif "t.me/" in text:
            chat_id = text.replace("https://t.me/", "").replace("t.me/", "").split("/")[0]
            # Agar private link hai to bot get_chat nahi kar payega, isliye try-except
        else:
            chat_id = text # Maan lete hain ye username hai

        try:
            # Group check karna
            chat = await client.get_chat(chat_id)
            
            # 4 Ghante ka time calculate karna
            until_date = datetime.now() + timedelta(hours=4)
            
            # Mute karna (Restrict)
            await client.restrict_chat_member(
                chat.id, 
                offender, 
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            # Appeal record save karna
            muted_db[str(offender)] = {"chat_id": chat.id, "chat_title": chat.title}
            
            # Group mein message bhejna
            await client.send_message(
                chat.id, 
                f"🚫 **Action:** Muted (4 Hours)\n"
                f"👤 **User:** `{offender}`\n"
                f"🛡️ **Reason:** DM Proof Verified\n"
                f"📝 **Note:** User DM mein safai de kar unmute ho sakta hai."
            )
            
            await message.reply_text(f"✅ User `{offender}` ko **{chat.title}** mein 4 ghante ke liye mute kar diya gaya hai.")
            del waiting_for_link[user_id]

        except Exception as e:
            await message.reply_text(
                f"❌ **Error:** `{e}`\n\n"
                "**Kaise theek karein?**\n"
                "1. Bot ko group mein Admin banayein.\n"
                "2. Agar group Private hai, to link ki jagah Group ID (-100...) bhejein."
            )
            if user_id in waiting_for_link:
                del waiting_for_link[user_id]
        return

    # --- STEP 3: APPEAL LOGIC (Muted User ke liye) ---
    u_id = str(user_id)
    u_name = f"@{message.from_user.username}" if message.from_user.username else None
    
    offender_key = None
    if u_id in muted_db: offender_key = u_id
    elif u_name and u_name in muted_db: offender_key = u_name

    if offender_key:
        # Bot ka Dimag (Language Processing)
        keywords = ["sorry", "kaam", "help", "work", "important", "zaroori", "galti", "puchna"]
        
        # Logic: Message 4 words se bada ho aur keyword ho
        if any(w in text.lower() for w in keywords) and len(text.split()) >= 4:
            try:
                target_chat = muted_db[offender_key]["chat_id"]
                
                # Unmute karna
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
                
                # Group notification
                await client.send_message(
                    target_chat, 
                    f"✅ **Auto-Unmute**\n"
                    f"👤 **User:** {message.from_user.mention}\n"
                    f"🤔 **Faisla:** User ki safai bot ko sahi lagi."
                )
                
                await message.reply_text("😇 Maine tumhari safai suni aur mujhe laga ki tumhe ek mauka dena chahiye. Group mein unmute kar diya hai!")
                del muted_db[offender_key]
            except Exception as e:
                print(f"Appeal Error: {e}")
        else:
            await message.reply_text("🤨 Ye safai sahi nahi hai. Thoda detail mein batao kyun DM kiya? (Kam se kam 5 words likho)")
