import asyncio
import random
import time
from typing import Optional, Union

from PIL import Image, ImageDraw, ImageFont
from pyrogram import enums, filters
from pyrogram.types import Message

from VIPMUSIC import app

# Spam Control
user_last_message_time = {}
user_command_count = {}
SPAM_THRESHOLD = 2
SPAM_WINDOW_SECONDS = 5

random_photo = [
    "https://telegra.ph/file/1949480f01355b4e87d26.jpg",
    "https://telegra.ph/file/3ef2cc0ad2bc548bafb30.jpg",
    "https://telegra.ph/file/a7d663cd2de689b811729.jpg",
    "https://telegra.ph/file/6f19dc23847f5b005e922.jpg",
    "https://telegra.ph/file/2973150dd62fd27a3a6ba.jpg",
]

bg_path = "assets/userinfo.png"
font_path = "assets/hiroko.ttf"

# --------------------------------------------------------------------------------- #

get_font = lambda font_size, font_path: ImageFont.truetype(font_path, font_size)

async def get_userinfo_img(
    bg_path: str,
    font_path: str,
    user_id: Union[int, str],
    profile_path: Optional[str] = None,
):
    bg = Image.open(bg_path)
    if profile_path:
        img = Image.open(profile_path)
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.pieslice([(0, 0), img.size], 0, 360, fill=255)
        circular_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask)
        resized = circular_img.resize((400, 400))
        bg.paste(resized, (440, 160), resized)

    img_draw = ImageDraw.Draw(bg)
    img_draw.text((529, 627), text=str(user_id).upper(), font=get_font(46, font_path), fill=(255, 255, 255))
    path = f"downloads/userinfo_img_{user_id}.png"
    bg.save(path)
    return path

async def get_user_status(user):
    x = user.status
    if x == enums.UserStatus.RECENTLY: return "ʀᴇᴄᴇɴᴛʟʏ"
    elif x == enums.UserStatus.LAST_WEEK: return "ʟᴀsᴛ ᴡᴇᴇᴋ"
    elif x == enums.UserStatus.LONG_AGO: return "ʟᴏɴɢ ᴛɪᴍᴇ ᴀɢᴏ"
    elif x == enums.UserStatus.OFFLINE: return "ᴏғғʟɪɴᴇ"
    elif x == enums.UserStatus.ONLINE: return "ᴏɴʟɪɴᴇ"
    return "ᴜɴᴋɴᴏᴡɴ"

# --------------------------------------------------------------------------------- #

INFO_TEXT = """
✨ **ᴜsᴇʀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ** ✨
━━━━━━━━━━━━━━━━━━━
🆔 **ᴜsᴇʀ ɪᴅ :** `{}`
👤 **ғɪʀsᴛ ɴᴀᴍᴇ :** `{}`
👥 **ʟᴀsᴛ ɴᴀᴍᴇ :** `{}`
📧 **ᴜsᴇʀɴᴀᴍᴇ :** @{}
🔗 **ᴍᴇɴᴛɪᴏɴ :** {}
🌐 **ᴅᴄ ɪᴅ :** `{}`
🕒 **sᴛᴀᴛᴜs :** `{}`
📝 **ʙɪᴏ :** `{}`
━━━━━━━━━━━━━━━━━━━
"""

@app.on_message(filters.command(["info", "userinfo"], prefixes=["/", "!", "%", ",", "", ".", "@", "#"]))
async def userinfo(_, message: Message):
    user_id = message.from_user.id
    current_time = time.time()
    
    # Spam Check
    last_time = user_last_message_time.get(user_id, 0)
    if current_time - last_time < SPAM_WINDOW_SECONDS:
        user_command_count[user_id] = user_command_count.get(user_id, 0) + 1
        if user_command_count[user_id] > SPAM_THRESHOLD:
            return await message.reply_text("⚠️ **ᴘʟᴇᴀsᴇ ᴅᴏɴ'ᴛ sᴘᴀᴍ! ᴡᴀɪᴛ 5 sᴇᴄᴏɴᴅs.**")
    else:
        user_command_count[user_id] = 1
        user_last_message_time[user_id] = current_time

    # Determine Target User
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        target_user = message.command[1]
    else:
        target_user = message.from_user.id

    try:
        user = await app.get_users(target_user)
        user_chat = await app.get_chat(user.id)
        
        status = await get_user_status(user)
        bio = user_chat.bio if user_chat.bio else "ɴᴏ ʙɪᴏ sᴇᴛ"
        last_name = user.last_name if user.last_name else "ɴᴏ ʟᴀsᴛ ɴᴀᴍᴇ"
        username = user.username if user.username else "ɴᴏ ᴜsᴇʀɴᴀᴍᴇ"
        
        # Profile Photo Logic
        if user.photo:
            photo_file = await app.download_media(user.photo.big_file_id)
            welcome_photo = await get_userinfo_img(bg_path, font_path, user.id, photo_file)
        else:
            welcome_photo = random.choice(random_photo)

        await message.reply_photo(
            photo=welcome_photo,
            caption=INFO_TEXT.format(
                user.id, user.first_name, last_name, username, user.mention, user.dc_id or "1", status, bio
            )
        )
    except Exception as e:
        await message.reply_text(f"❌ **ᴇʀʀᴏʀ:** `{str(e)}`")

# --------------------------------------------------------------------------------- #

__MODULE__ = "ᴜsᴇʀ ɪɴғᴏ"
__HELP__ = """
✨ **ɪɴғᴏ ᴍᴏᴅᴜʟᴇ** ✨

● `/info` : ɢᴇᴛ ʏᴏᴜʀ ᴏᴡɴ ɪɴғᴏ.
● `/info [ʀᴇᴘʟʏ]` : ɢᴇᴛ ʀᴇᴘʟɪᴇᴅ ᴜsᴇʀ ɪɴғᴏ.
● `/info [ᴜsᴇʀɴᴀᴍᴇ/ɪᴅ]` : ɢᴇᴛ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ ɪɴғᴏ.
"""
