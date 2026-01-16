import asyncio
import re
from datetime import datetime
from logging import getLogger
from time import time

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFont
from pyrogram import enums, filters
from pyrogram.types import (ChatMemberUpdated, InlineKeyboardButton,
                            InlineKeyboardMarkup)
from pymongo import MongoClient
from pytz import timezone

import config
from config import MONGO_DB_URI
from VIPMUSIC import app

# --- CONFIG & DATABASE ---
LOGGER = getLogger(__name__)
user_last_message_time = {}
user_command_count = {}
SPAM_THRESHOLD = 2
SPAM_WINDOW_SECONDS = 5

welcomedb = MongoClient(MONGO_DB_URI)
status_db = welcomedb.welcome_status_db.status

# --- HELPERS ---
def convert_to_small_caps(text):
    mapping = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘϙʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘϙʀꜱᴛᴜᴠᴡxʏᴢ",
    )
    return text.translate(mapping)

class temp:
    MELCOW = {}

def circle(pfp, size=(80, 80)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    
    # Simple Aesthetic Border
    border = Image.new("RGBA", (size[0] + 6, size[1] + 6), (0, 0, 0, 0))
    draw_b = ImageDraw.Draw(border)
    draw_b.ellipse((0, 0, size[0] + 6, size[1] + 6), outline="#FFFFFF", width=3)
    border.paste(pfp, (3, 3), pfp)
    return border

def welcomepic(user_id, user_names, chat_name, user_photo):
    try:
        background = Image.open("assets/wel2.png")
        user_img = Image.open(user_photo).convert("RGBA")
        user_img = circle(user_img, size=(230, 230))
        
        # Background pe paste karna (Aapke coordinates ke hisab se)
        background.paste(user_img, (827, 260), user_img)
        
        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype("assets/font.ttf", size=35)
        
        # Image pe text writing
        draw.text((510, 520), f"NAME: {user_names[:15]}", fill="white", font=font)
        draw.text((510, 570), f"ID: {user_id}", fill="white", font=font)

        path = f"downloads/welcome#{user_id}.png"
        background.save(path)
        return path
    except Exception as e:
        LOGGER.error(e)
        return "assets/wel2.png"

# --- DB FUNCTIONS ---
async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

async def set_welcome_status(chat_id, state):
    status_db.update_one({"chat_id": chat_id}, {"$set": {"welcome": state}}, upsert=True)

# --- COMMANDS ---
@app.on_message(filters.command("welcome") & ~filters.private)
async def auto_state(_, message):
    user_id = message.from_user.id
    if message.from_user.id in user_last_message_time:
        if time() - user_last_message_time[user_id] < SPAM_WINDOW_SECONDS:
            return
    user_last_message_time[user_id] = time()

    if len(message.command) < 2:
        return await message.reply_text("**ᴜsᴀɢᴇ:**\n**/welcome [on|off]**")

    user = await app.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
        return await message.reply_text("**ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs!**")

    state = message.command[1].lower()
    if state in ["on", "off"]:
        await set_welcome_status(message.chat.id, state)
        await message.reply_text(f"**ᴡᴇʟᴄᴏᴍᴇ ɴᴏᴛɪғɪᴄᴀᴛɪᴏɴ sᴇᴛ ᴛᴏ {state.upper()}**")
    else:
        await message.reply_text("**ᴜsᴀɢᴇ: /welcome [on|off]**")

# --- MAIN HANDLER ---
@app.on_chat_member_updated(filters.group, group=-4)
async def greet_new_members(_, member: ChatMemberUpdated):
    if not member.new_chat_member or member.old_chat_member:
        return
        
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    count = await app.get_chat_members_count(chat_id)
    
    # Time logic
    ist = timezone('Asia/Kolkata')
    joined_time = datetime.now(ist).strftime('%I:%M %p')

    # Profile Photo logic
    try:
        user_photo = await app.download_media(user.photo.big_file_id, file_name=f"pp{user.id}.png")
    except:
        user_photo = "assets/nodp.png"

    # Photo generate
    welcomeimg = welcomepic(user.id, user.first_name, member.chat.title, user_photo)

    # --- UNIQUE MINIMALIST CAPTION ---
    # Tree style: ┌ ├ └
    cap = (
        f"<b>⌯ {convert_to_small_caps('ɴᴇᴡ ᴇɴᴛʀʏ')} ⌯</b>\n"
        f"<b>{user.mention}</b>\n\n"
        f"<b>┌ ɪᴅ :</b> <code>{user.id}</code>\n"
        f"<b>├ ᴄᴏᴜɴᴛ :</b> {count}\n"
        f"<b>├ ᴛɪᴍᴇ :</b> {joined_time}\n"
        f"<b>└ ɢʀᴏᴜᴘ :</b> {convert_to_small_caps(member.chat.title[:15])}\n\n"
        f"<b>⌬ {convert_to_small_caps('ᴘᴏᴡᴇʀᴇᴅ ʙʏ')} {app.mention}</b>"
    )

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"✥ {convert_to_small_caps('ᴀᴅᴅ ᴍᴇ')} ✥", url=f"https://t.me/{app.username}?startgroup=true")]]
    )

    # Delete old welcome if exists
    old_msg = temp.MELCOW.get(f"welcome-{chat_id}")
    if old_msg:
        try: await old_msg.delete()
        except: pass

    # Send new welcome
    msg = await app.send_photo(chat_id, photo=welcomeimg, caption=cap, reply_markup=reply_markup)
    temp.MELCOW[f"welcome-{chat_id}"] = msg

__MODULE__ = "Wᴇʟᴄᴏᴍᴇ"
__HELP__ = "/welcome [on/off] - To enable/disable welcome messages."
