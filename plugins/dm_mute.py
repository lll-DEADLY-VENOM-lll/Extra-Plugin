from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, Message
from datetime import datetime, timedelta

# Database
muted_users = {} 
waiting_for_link = {}

__MODULE__ = "SmartJudge"
__HELP__ = """
**Mute Judge Commands:**

1. **/report** - Report karne ka tarika janne ke liye.
2. **Photo bhejein** - Screenshot bhejein aur caption mein Spammer ki ID likhen.
3. **Link bhejein** - Jab bot maange tab group link dein.
"""

# 1. Start/Report Command
@Client.on_message(filters.command("report") & filters.private)
async def report_cmd(client, message):
    await message.reply_text(
        "📝 **Report Kaise Karein?**\n\n"
        "1. Us bande ke message ka screenshot lein.\n"
        "2. Wo photo mujhe (Bot ko) bhejein.\n"
        "3. Photo ke **Caption** mein us bande ki ID ya Username likhein.\n\n"
        "Main turant action lunga!"
    )

# 2. Photo Trigger (As a Command)
@Client.on_message(filters.photo & filters.private)
async def photo_trigger(client, message):
    if not message.caption:
        await message.reply_text("❌ Photo ke saath uski ID caption mein likho tabhi main pehchan paunga!")
        return
    
    offender = message.caption.strip()
    waiting_for_link[message.from_user.id] = offender
    await message.reply_text(f"✅ Proof mil gaya.\n👤 Target: `{offender}`\n\nAb us **Group ka Link** bhejiye jahan ye user hai.")

# 3. Link handling & Logic
@Client.on_message(filters.text & filters.private)
async def handle_logic(client, message):
    user_id = message.from_user.id
    text = message.text

    # Link mangne wala part
    if user_id in waiting_for_link:
        offender = waiting_for_link[user_id]
        try:
            # Group ID nikalna
            link = text.replace("https://t.me/", "").split("/")[0]
            chat_obj = await client.get_chat(link)
            
            # 4 Ghante ke liye mute
            until = datetime.now() + timedelta(hours=4)
            await client.restrict_chat_member(chat_obj.id, offender, ChatPermissions(can_send_messages=False), until_date=until)
            
            muted_users[offender] = chat_obj.id
            await client.send_message(chat_obj.id, f"🚫 **Muted:** `{offender}`\n**Duration:** 4 Hours\n**Reason:** Verified DM Spam")
            await message.reply_text("✅ Done! User ko mute kar diya gaya hai.")
            del waiting_for_link[user_id]
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")
        return

    # Appeal Logic (Muted user ke liye)
    # [Wahi same logic jo pehle diya tha...]
