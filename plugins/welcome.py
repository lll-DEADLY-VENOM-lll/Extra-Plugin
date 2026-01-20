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

# --- Pixel Perfect Image Processing --- #

def make_round(pfp, size=(230, 230)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    
    # Premium Glow Border (Cyan for User, Gold-ish for Frame)
    bg = Image.new("RGBA", (size[0]+12, size[1]+12), (0, 0, 0, 0))
    draw_bg = ImageDraw.Draw(bg)
    draw_bg.ellipse((0, 0, size[0]+12, size[1]+12), outline=(0, 255, 255, 200), width=6)
    bg.paste(pfp, (6, 6), pfp)
    return bg

def create_welcome_card(u_id, u_first, u_username, c_name, u_pfp, c_pfp):
    try:
        # Load Background (1200x600 recommended)
        bg_path = "assets/wel2.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 600))
        else:
            bg = Image.new("RGBA", (1200, 600), (15, 15, 25))

        # Process Photos with standard size
        user_img = make_round(Image.open(u_pfp), (235, 235))
        chat_img = make_round(Image.open(c_pfp), (235, 235))

        # Coordinate Adjustment (Centered inside your gold frames)
        # Left Frame Center
        bg.paste(user_img, (125, 155), user_img) 
        # Right Frame Center
        bg.paste(chat_img, (835, 155), chat_img) 

        # Info Box (Compact & Slim)
        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Rounded rectangle for info - Center Bottom
        draw_ov.rounded_rectangle((350, 440, 850, 560), radius=25, fill=(0, 0, 0, 180))
        bg = Image.alpha_composite(bg, overlay)

        # Fonts Setup
        try:
            # Font paths change according to your server
            f_title = ImageFont.truetype("assets/font.ttf", 52)
            f_info = ImageFont.truetype("assets/font.ttf", 30)
        except:
            f_title = f_info = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)

        # Welcome Text (Perfectly Centered)
        draw.text((600, 150), "WELCOME TO", font=f_title, fill=(255, 255, 255), anchor="mm")
        
        # Group Name Fix (Clean rendering to avoid boxes)
        clean_c_name = c_name.encode('ascii', 'ignore').decode('ascii') or "GROUP"
        draw.text((600, 215), f"{clean_c_name[:15].upper()}", font=f_title, fill=(0, 255, 255), anchor="mm")

        # User Details in Info Box
        draw.text((380, 455), f"NAME: {u_first[:15]}", font=f_info, fill=(255, 255, 255))
        draw.text((380, 488), f"ID: {u_id}", font=f_info, fill=(0, 255, 255))
        draw.text((380, 521), f"USER: {u_username[:15]}", font=f_info, fill=(255, 255, 255))

        out = f"downloads/wel_{u_id}.png"
        bg.save(out)
        return out
    except Exception as e:
        LOGGER.error(f"Draw Error: {e}")
        return None

# --- Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
async def greet_member(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    count = await app.get_chat_members_count(chat_id)
    
    # Download Avatars
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"
    c_p = await app.download_media(member.chat.photo.big_file_id, f"c{chat_id}.png") if member.chat.photo else "assets/nodp.png"

    loop = asyncio.get_running_loop()
    welcome_file = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, f"@{user.username}" if user.username else "No User", member.chat.title, u_p, c_p)

    if welcome_file:
        username = f"@{user.username}" if user.username else "ɴᴏᴛ sᴇᴛ"
        # SLIM BOX CAPTION
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        # Cleanup
        for f in [welcome_file, u_p, c_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                os.remove(f)

@app.on_message(filters.command("welcome") & ~filters.private)
async def toggle_welcome(_, m):
    user = await app.get_chat_member(m.chat.id, m.from_user.id)
    if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return
    if len(m.command) < 2: return
    state = m.command[1].lower()
    await set_welcome_status(m.chat.id, state)
    await m.reply_text(f"✅ Welcome set to {state.upper()}")

__MODULE__ = "Welcome"
