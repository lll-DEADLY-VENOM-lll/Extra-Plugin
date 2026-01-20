import asyncio
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import enums, filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from VIPMUSIC import app
from config import MONGO_DB_URI

# Database Setup
welcomedb = MongoClient(MONGO_DB_URI)
status_db = welcomedb.welcome_status_db.status

# --- Slim Utilities --- #

async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

async def set_welcome_status(chat_id, state):
    status_db.update_one({"chat_id": chat_id}, {"$set": {"welcome": state}}, upsert=True)

def make_round(pfp, size=(200, 200)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    
    # Slim Neon Border
    bg = Image.new("RGBA", (size[0]+8, size[1]+8), (0, 0, 0, 0))
    draw_bg = ImageDraw.Draw(bg)
    draw_bg.ellipse((0, 0, size[0]+8, size[1]+8), outline=(0, 255, 255, 200), width=4)
    bg.paste(pfp, (4, 4), pfp)
    return bg

# --- Compact Image Design --- #

def create_welcome_card(u_id, u_first, u_username, c_name, u_pfp, c_pfp):
    try:
        bg_path = "assets/wel2.png"
        bg = Image.open(bg_path).convert("RGBA").resize((1200, 600)) if os.path.exists(bg_path) else Image.new("RGBA", (1200, 600), (10, 10, 15))

        # Process Photos (Slimmer size)
        user_img = make_round(Image.open(u_pfp), (210, 210))
        chat_img = make_round(Image.open(c_pfp), (210, 210))

        # Aligned Positions
        bg.paste(chat_img, (120, 150), chat_img)
        bg.paste(user_img, (870, 150), user_img)

        # Compact Glass Panel (Slimmer Width)
        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Position: Center-Bottom, Width: Slim
        draw_ov.rounded_rectangle((380, 430, 820, 550), radius=20, fill=(0, 0, 0, 170))
        bg = Image.alpha_composite(bg, overlay)

        draw = ImageDraw.Draw(bg)
        try:
            f_title = ImageFont.truetype("assets/font.ttf", 45)
            f_small = ImageFont.truetype("assets/font.ttf", 28)
        except:
            f_title = f_small = ImageFont.load_default()

        # Text on Image (Centered)
        draw.text((600, 160), "WELCOME TO", font=f_title, fill=(255, 255, 255), anchor="mm")
        draw.text((600, 215), f"{c_name[:18]}", font=f_title, fill=(0, 255, 255), anchor="mm")

        # Slim info in box
        draw.text((410, 445), f"NAME: {u_first[:15]}", font=f_small, fill=(255, 255, 255))
        draw.text((410, 475), f"ID: {u_id}", font=f_small, fill=(0, 255, 255))
        draw.text((410, 505), f"USER: {u_username[:15]}", font=f_small, fill=(255, 255, 255))

        out = f"downloads/w_{u_id}.png"
        bg.save(out)
        return out
    except Exception as e:
        print(f"Error: {e}")
        return None

# --- Handlers --- #

@app.on_chat_member_updated(filters.group, group=5)
async def member_join_handler(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    if await get_welcome_status(member.chat.id) == "off":
        return

    user = member.new_chat_member.user
    count = await app.get_chat_members_count(member.chat.id)
    
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"
    c_p = await app.download_media(member.chat.photo.big_file_id, f"c{member.chat.id}.png") if member.chat.photo else "assets/nodp.png"

    loop = asyncio.get_running_loop()
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, f"@{user.username}" if user.username else "No User", member.chat.title, u_p, c_p)

    if card:
        # SLIM BOX CAPTION (Reduced dashes for better mobile fit)
        caption = (
            f"✨ <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {member.chat.title}</b>\n\n"
            f"<b>┏━━━━━━━━━━━━━━━━━━┓</b>\n"
            f"<b>➻ 👤 ᴜsᴇʀ :</b> {user.mention}\n"
            f"<b>➻ 🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>➻ 🔗 ᴜsᴇʀɴᴀᴍᴇ :</b> @{user.username if user.username else 'ɴᴏᴛ sᴇᴛ'}\n"
            f"<b>➻ 🏆 ᴍᴇᴍʙᴇʀ ɴᴏ :</b> {count}\n"
            f"<b>┗━━━━━━━━━━━━━━━━━━┛</b>"
        )
        
        await app.send_photo(
            member.chat.id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀᴛ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        for f in [card, u_p, c_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                os.remove(f)

@app.on_message(filters.command("welcome") & ~filters.private)
async def welcome_toggle(_, m):
    user = await app.get_chat_member(m.chat.id, m.from_user.id)
    if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return
    if len(m.command) < 2: return
    state = m.command[1].lower()
    await set_welcome_status(m.chat.id, state)
    await m.reply_text(f"✅ Welcome {state.upper()}")

__MODULE__ = "Welcome"
