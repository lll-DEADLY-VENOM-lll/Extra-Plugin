import asyncio
import random
import os
from time import time
from typing import Optional, Union

from PIL import Image, ImageDraw, ImageFont
from pyrogram import enums, filters
from pyrogram.types import Message

# Spy se app import ho raha hai
from Spy import app

# --- Anti-Spam Logic ---
user_last_message_time = {}
user_command_count = {}
SPAM_THRESHOLD = 2
SPAM_WINDOW_SECONDS = 5

# --- Photos ---
random_photo = [
    "https://telegra.ph/file/1949480f01355b4e87d26.jpg",
    "https://telegra.ph/file/3ef2cc0ad2bc548bafb30.jpg",
    "https://telegra.ph/file/a7d663cd2de689b811729.jpg",
    "https://telegra.ph/file/6f19dc23847f5b005e922.jpg",
    "https://telegra.ph/file/2973150dd62fd27a3a6ba.jpg",
]

# --- Image Processing Helpers ---
get_font = lambda font_size, font_path: ImageFont.truetype(font_path, font_size)

async def get_userinfo_img(
    bg_path: str,
    font_path: str,
    user_id: Union[int, str],
    profile_path: Optional[str] = None,
):
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    bg = Image.open(bg_path)

    if profile_path:
        img = Image.open(profile_path).convert("RGBA")
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.pieslice([(0, 0), img.size], 0, 360, fill=255)

        circular_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask)
        resized = circular_img.resize((400, 400))
        bg.paste(resized, (440, 160), resized)

    img_draw = ImageDraw.Draw(bg)
    # Drawing User ID on image
    img_draw.text(
        (529, 627),
        text=str(user_id).upper(),
        font=get_font(46, font_path),
        fill=(255, 255, 255),
    )

    path = f"downloads/userinfo_img_{user_id}.png"
    bg.save(path)
    return path

# Paths (Ensure these files exist in your bot's assets folder)
bg_path = "assets/userinfo.png"
font_path = "assets/hiroko.ttf"

INFO_TEXT = """**
❅─────✧❅✦❅✧─────❅
            ✦ ᴜsᴇʀ ɪɴғᴏ ✦

➻ ᴜsᴇʀ ɪᴅ ‣ **`{}`
**➻ ғɪʀsᴛ ɴᴀᴍᴇ ‣ **{}
**➻ ʟᴀsᴛ ɴᴀᴍᴇ ‣ **{}
**➻ ᴜsᴇʀɴᴀᴍᴇ ‣ **`{}`
**➻ ᴍᴇɴᴛɪᴏɴ ‣ **{}
**➻ ʟᴀsᴛ sᴇᴇɴ ‣ **{}
**➻ ᴅᴄ ɪᴅ ‣ **{}
**➻ ʙɪᴏ ‣ **`{}`

**❅─────✧❅✦❅✧─────❅**
"""

async def userstatus(user_id):
    try:
        user = await app.get_users(user_id)
        x = user.status
        if x == enums.UserStatus.RECENTLY: return "Recently"
        elif x == enums.UserStatus.LAST_WEEK: return "Last week"
        elif x == enums.UserStatus.LONG_AGO: return "Long time ago"
        elif x == enums.UserStatus.OFFLINE: return "Offline"
        elif x == enums.UserStatus.ONLINE: return "Online"
        else: return "Unknown"
    except:
        return "Not Available"

# --- Main Info Command ---

@app.on_message(filters.command(["info", "userinfo"], prefixes=["/", "!", "%", ",", "", ".", "@", "#"]))
async def userinfo(_, message: Message):
    user_id = message.from_user.id
    curr_time = time()
    
    # Anti-Spam
    last_time = user_last_message_time.get(user_id, 0)
    if curr_time - last_time < SPAM_WINDOW_SECONDS:
        user_command_count[user_id] = user_command_count.get(user_id, 0) + 1
        if user_command_count[user_id] > SPAM_THRESHOLD:
            hu = await message.reply_text(f"**{message.from_user.mention}, ᴘʟᴇᴀsᴇ ᴅᴏɴ'ᴛ sᴘᴀᴍ! ᴛʀʏ ᴀɢᴀɪɴ ɪɴ 5s.**")
            await asyncio.sleep(3)
            return await hu.delete()
    else:
        user_command_count[user_id] = 1
        user_last_message_time[user_id] = curr_time

    # Identify User
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        target_user = message.command[1]
    else:
        target_user = message.from_user.id

    processing = await message.reply_text("`Fetching Information...`")

    try:
        user = await app.get_users(target_user)
        user_info = await app.get_chat(user.id) # For Bio
        
        status = await userstatus(user.id)
        dc_id = user.dc_id or "N/A"
        first_name = user.first_name
        last_name = user.last_name or "None"
        username = f"@{user.username}" if user.username else "None"
        mention = user.mention
        bio = user_info.bio or "No bio set"

        photo_to_send = None
        if user.photo:
            photo_path = await app.download_media(user.photo.big_file_id)
            if os.path.exists(bg_path) and os.path.exists(font_path):
                photo_to_send = await get_userinfo_img(bg_path, font_path, user.id, photo_path)
            else:
                photo_to_send = photo_path # Send real photo if assets missing
        else:
            photo_to_send = random.choice(random_photo)

        await message.reply_photo(
            photo=photo_to_send,
            caption=INFO_TEXT.format(user.id, first_name, last_name, username, mention, status, dc_id, bio)
        )
        await processing.delete()
        
        # Cleanup
        if photo_to_send.startswith("downloads/userinfo_img_"):
            if os.path.exists(photo_to_send): os.remove(photo_to_send)

    except Exception as e:
        await processing.edit(f"**Error:** `{str(e)}`")

__MODULE__ = "Usᴇʀ Iɴғᴏ"
__HELP__ = """
**Usᴇʀ Iɴғᴏ Cᴏᴍᴍᴀɴᴅs:**
/ɪɴғᴏ [ᴜsᴇʀɪᴅ/ᴜsᴇʀɴᴀᴍᴇ]: Gᴇᴛ ɪɴғᴏ ᴏғ ᴀ ᴜsᴇʀ.
/ᴜsᴇʀɪɴғᴏ (ʀᴇᴘʟʏ): Gᴇᴛ ɪɴғᴏ ᴏғ ʀᴇᴘʟɪᴇᴅ ᴜsᴇʀ.
"""   
