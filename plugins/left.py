import asyncio
import random
from typing import Optional, Union

from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import RPCError

from VIPMUSIC import app

# --- MODULE SETTINGS ---
__MODULE__ = "ʟᴇғᴛ ɢʀᴏᴜᴘ"
__HELP__ = """
**Leave Log Settings:**

/leavelog [on/off] - Enable or Disable the group leave notification photo.

**Note:** 
- Only Admins can use this command.
- Leave messages are automatically deleted after 30 seconds.
"""

# Dictionary to store status per chat (Resets on bot restart)
# For permanent storage, replace this with a database call.
LEAVE_STATE = {}

random_photo = [
    "https://telegra.ph/file/1949480f01355b4e87d26.jpg",
    "https://telegra.ph/file/3ef2cc0ad2bc548bafb30.jpg",
    "https://telegra.ph/file/a7d663cd2de689b811729.jpg",
    "https://telegra.ph/file/6f19dc23847f5b005e922.jpg",
    "https://telegra.ph/file/2973150dd62fd27a3a6ba.jpg",
]

bg_path = "assets/userinfo.png"
font_path = "assets/hiroko.ttf"

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
    img_draw.text(
        (529, 627),
        text=str(user_id).upper(),
        font=get_font(46, font_path),
        fill=(255, 255, 255),
    )
    path = f"downloads/userinfo_img_{user_id}.png"
    bg.save(path)
    return path

# --- ON/OFF COMMAND ---
@app.on_message(filters.command("leavelog") & filters.group)
async def toggle_leave_log(client, message: Message):
    # Check if the sender is an admin
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if not member.privileges:
        return await message.reply_text("❌ Only administrators can change LeaveLog settings.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/leavelog on` or `/leavelog off`")

    input_state = message.command[1].lower()
    
    if input_state == "on":
        LEAVE_STATE[message.chat.id] = True
        await message.reply_text("✅ **LeaveLog has been enabled for this group.**")
    elif input_state == "off":
        LEAVE_STATE[message.chat.id] = False
        await message.reply_text("❌ **LeaveLog has been disabled for this group.**")
    else:
        await message.reply_text("Invalid argument. Use `on` or `off`.")

# --- EVENT HANDLER ---
@app.on_chat_member_updated(filters.group, group=-7)
async def member_has_left(client: app, member: ChatMemberUpdated):
    # Check if LeaveLog is enabled for this chat (Default is OFF)
    if not LEAVE_STATE.get(member.chat.id, False):
        return

    # Detection logic for leaving
    if (
        not member.new_chat_member
        and member.old_chat_member 
        and member.old_chat_member.status not in {"banned", "left", "restricted"}
    ):
        user = member.old_chat_member.user if member.old_chat_member else member.from_user
        
        try:
            if user.photo:
                photo = await app.download_media(user.photo.big_file_id)
                leave_photo = await get_userinfo_img(
                    bg_path=bg_path,
                    font_path=font_path,
                    user_id=user.id,
                    profile_path=photo,
                )
            else:
                leave_photo = random.choice(random_photo)

            caption = (
                f"**#New_Member_Left**\n\n"
                f"**๏** {user.mention} **ʜᴀs ʟᴇғᴛ ᴛʜɪs ɢʀᴏᴜᴘ**\n"
                f"**๏ sᴇᴇ ʏᴏᴜ sᴏᴏɴ ᴀɢᴀɪɴ..!**"
            )
            
            msg = await client.send_photo(
                chat_id=member.chat.id,
                photo=leave_photo,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("๏ ᴠɪᴇᴡ ᴜsᴇʀ ๏", user_id=user.id)]]
                ),
            )

            # Auto-delete after 30 seconds
            async def delete_after_delay():
                await asyncio.sleep(30)
                try:
                    await msg.delete()
                except:
                    pass

            asyncio.create_task(delete_after_delay())

        except RPCError as e:
            print(f"LeaveLog Error: {e}")
            return
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return
