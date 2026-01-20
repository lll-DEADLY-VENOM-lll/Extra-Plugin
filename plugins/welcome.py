import asyncio
import os
from datetime import datetime
from logging import getLogger
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import enums, filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from VIPMUSIC import app
from config import MONGO_DB_URI

LOGGER = getLogger(__name__)

# Database Setup
welcomedb = MongoClient(MONGO_DB_URI)
status_db = welcomedb.welcome_status_db.status

# --- Utilities --- #

async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

async def set_welcome_status(chat_id, state):
    status_db.update_one({"chat_id": chat_id}, {"$set": {"welcome": state}}, upsert=True)

# --- Improved Image Processing --- #

def make_round(pfp, size=(220, 220)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    
    # Simple Glow Border
    bg = Image.new("RGBA", (size[0]+10, size[1]+10), (0, 0, 0, 0))
    draw_bg = ImageDraw.Draw(bg)
    draw_bg.ellipse((0, 0, size[0]+10, size[1]+10), outline=(0, 255, 255, 180), width=5)
    bg.paste(pfp, (5, 5), pfp)
    return bg

def create_welcome_card(u_id, u_first, u_username, c_name, u_pfp, c_pfp):
    try:
        # Load Background
        bg_path = "assets/wel2.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 600))
        else:
            bg = Image.new("RGBA", (1200, 600), (15, 15, 25))

        # Process Photos
        user_img = make_round(Image.open(u_pfp), (220, 220))
        chat_img = make_round(Image.open(c_pfp), (220, 220))

        # Positions (Adjusted based on your screenshot)
        bg.paste(chat_img, (110, 140), chat_img) # Left: Group DP
        bg.paste(user_img, (870, 140), user_img) # Right: User DP

        # Draw Info Box (Smaller & Cleaner)
        draw = ImageDraw.Draw(bg)
        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Compact Box
        draw_ov.rounded_rectangle((320, 420, 880, 560), radius=25, fill=(0, 0, 0, 160))
        bg = Image.alpha_composite(bg, overlay)

        # Fonts (Safe Fallback)
        try:
            f_title = ImageFont.truetype("assets/font.ttf", 50)
            f_info = ImageFont.truetype("assets/font.ttf", 32)
        except:
            f_title = f_info = ImageFont.load_default()

        # Text on Image
        draw = ImageDraw.Draw(bg)
        # Welcome Title
        draw.text((600, 150), "WELCOME TO", font=f_title, fill=(255, 255, 255), anchor="mm")
        # Group Name (Clean Text)
        draw.text((600, 210), f"{c_name[:20]}", font=f_title, fill=(0, 255, 255), anchor="mm")

        # User Details in Box
        draw.text((350, 440), f"NAME: {u_first[:15]}", font=f_info, fill=(255, 255, 255))
        draw.text((350, 480), f"USER ID: {u_id}", font=f_info, fill=(0, 255, 255))
        draw.text((350, 520), f"USER: {u_username[:18]}", font=f_info, fill=(255, 255, 255))

        out = f"downloads/welcome_{u_id}.png"
        bg.save(out)
        return out
    except Exception as e:
        LOGGER.error(f"Draw Error: {e}")
        return None

# --- Handlers --- #

@app.on_message(filters.command("welcome") & ~filters.private)
async def welcome_toggle(_, m):
    # Admin check
    check = await app.get_chat_member(m.chat.id, m.from_user.id)
    if check.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return await m.reply_text("❌ **Admins Only!**")
    
    if len(m.command) < 2:
        return await m.reply_text("✨ `/welcome on` | `/welcome off`")
    
    state = m.command[1].lower()
    await set_welcome_status(m.chat.id, "on" if state == "on" else "off")
    await m.reply_text(f"✅ **Welcome status updated to {state.upper()}**")

@app.on_chat_member_updated(filters.group, group=4)
async def on_join(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    count = await app.get_chat_members_count(chat_id)
    
    # Download Photos
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"
    c_p = await app.download_media(member.chat.photo.big_file_id, f"c{chat_id}.png") if member.chat.photo else "assets/nodp.png"

    # Async Image Task
    loop = asyncio.get_running_loop()
    welcome_file = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, f"@{user.username}" if user.username else "No User", member.chat.title, u_p, c_p)

    if welcome_file:
        username = f"@{user.username}" if user.username else "ɴᴏᴛ sᴇᴛ"
        # Caption Style
        caption = (
            f"✨ <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {member.chat.title}</b>\n\n"
            f"┏━━━━━━━━━━━━━━━━━━┓\n"
            f"➻ 👤 <b>ᴜsᴇʀ :</b> {user.mention}\n"
            f"➻ 🆔 <b>ɪᴅ :</b> <code>{user.id}</code>\n"
            f"➻ 🔗 <b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}\n"
            f"➻ 🏆 <b>ᴍᴇᴍʙᴇʀ ɴᴏ :</b> {count}\n"
            f"┗━━━━━━━━━━━━━━━━━━┛"
        )
        
        await app.send_photo(
            chat_id, 
            photo=welcome_file, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀᴛ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        # Cleanup
        for f in [welcome_file, u_p, c_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                os.remove(f)

__MODULE__ = "Welcome"
