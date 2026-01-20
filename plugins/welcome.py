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

# --- Aesthetic Utilities --- #

async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

async def set_welcome_status(chat_id, state):
    status_db.update_one({"chat_id": chat_id}, {"$set": {"welcome": state}}, upsert=True)

# --- Premium Image Processing --- #

def draw_premium_circle(pfp, size=(250, 250), color=(0, 255, 255)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)

    aura_size = (size[0] + 40, size[1] + 40)
    aura = Image.new("RGBA", aura_size, (0, 0, 0, 0))
    draw_aura = ImageDraw.Draw(aura)
    
    # Neon multi-ring
    for i in range(1, 10):
        alpha = 255 - (i * 25)
        draw_aura.ellipse((i, i, aura_size[0]-i, aura_size[1]-i), outline=color + (alpha,), width=3)
    
    aura = aura.filter(ImageFilter.GaussianBlur(3))
    aura.paste(pfp, (20, 20), pfp)
    return aura

def create_welcome_card(u_id, u_name, c_name, u_pfp, c_pfp):
    try:
        bg_path = "assets/wel2.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 600))
        else:
            bg = Image.new("RGBA", (1200, 600), (10, 10, 20))

        # Glassmorphism Panel
        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle((60, 430, 1140, 570), radius=35, fill=(0, 0, 0, 150))
        bg = Image.alpha_composite(bg, overlay)

        # Process Avatars
        user_img = draw_premium_circle(Image.open(u_pfp), (240, 240), (0, 255, 255))
        chat_img = draw_premium_circle(Image.open(c_pfp), (240, 240), (255, 0, 150))

        bg.paste(chat_img, (80, 130), chat_img)
        bg.paste(user_img, (880, 130), user_img)

        draw = ImageDraw.Draw(bg)
        try:
            f_huge = ImageFont.truetype("assets/font.ttf", 60)
            f_main = ImageFont.truetype("assets/font.ttf", 45)
            f_sub = ImageFont.truetype("assets/font.ttf", 35)
        except:
            f_huge = f_main = f_sub = ImageFont.load_default()

        # Welcome Text & Group Name on Image
        draw.text((440, 100), "WELCOME TO", font=f_main, fill=(255, 255, 255))
        draw.text((440, 170), f"{c_name[:20].upper()}", font=f_huge, fill=(0, 255, 255))

        # User Info on Panel
        draw.text((380, 455), f"NAME: {u_name[:20]}", font=f_sub, fill=(255, 255, 255))
        draw.text((380, 510), f"USER ID: {u_id}", font=f_sub, fill=(0, 255, 255))

        out = f"downloads/wel_{u_id}.png"
        bg.save(out, quality=95)
        return out
    except Exception as e:
        LOGGER.error(e)
        return None

# --- Handlers --- #

@app.on_message(filters.command("welcome") & ~filters.private)
async def welcome_cmd(_, m):
    check = await app.get_chat_member(m.chat.id, m.from_user.id)
    if check.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return await m.reply_text("❌ **Sirf admins hi use kar sakte hain!**")
    
    if len(m.command) < 2:
        return await m.reply_text("✨ `/welcome on` | `/welcome off`")
    
    state = m.command[1].lower()
    await set_welcome_status(m.chat.id, state)
    await m.reply_text(f"✅ Welcome set to **{state.upper()}**")

@app.on_chat_member_updated(filters.group, group=3)
async def member_has_joined(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    chat_name = member.chat.title
    count = await app.get_chat_members_count(chat_id)
    
    # Download Photos
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"
    c_p = await app.download_media(member.chat.photo.big_file_id, f"c{chat_id}.png") if member.chat.photo else "assets/nodp.png"

    # Async Image Gen
    loop = asyncio.get_running_loop()
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, chat_name, u_p, c_p)

    if card:
        username = f"@{user.username}" if user.username else "ɴᴏᴛ sᴇᴛ"
        # Premium Box Caption with Group Name
        caption = (
            f"✨ <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {chat_name}</b>\n\n"
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"➻ 👤 <b>ᴜsᴇʀ :</b> {user.mention}\n"
            f"➻ 🆔 <b>ɪᴅ :</b> <code>{user.id}</code>\n"
            f"➻ 🔗 <b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}\n"
            f"➻ 🏆 <b>ᴍᴇᴍʙᴇʀ ɴᴏ :</b> {count}\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        )
        
        button = InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀᴛ", url=f"https://t.me/{app.username}?startgroup=true")
        ]])

        await app.send_photo(chat_id, photo=card, caption=caption, reply_markup=button)

        # Clean Up
        for f in [card, u_p, c_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                os.remove(f)

__MODULE__ = "Welcome"
__HELP__ = "/welcome [on/off] - Toggle premium welcome with Group name branding."
