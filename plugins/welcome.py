import asyncio
import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import enums, filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from VIPMUSIC import app
from config import MONGO_DB_URI

# --- Database Setup --- #
welcomedb = MongoClient(MONGO_DB_URI)
status_db = welcomedb.welcome_status_db.status

async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

async def set_welcome_status(chat_id, state):
    status_db.update_one({"chat_id": chat_id}, {"$set": {"welcome": state}}, upsert=True)

# --- Premium Image Logic --- #

def make_round(pfp, size=(240, 240)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    
    canvas = Image.new("RGBA", (size[0]+12, size[1]+12), (0, 0, 0, 0))
    draw_can = ImageDraw.Draw(canvas)
    # Golden-Cyan mix border for premium look
    draw_can.ellipse((0, 0, size[0]+12, size[1]+12), outline=(0, 255, 255, 200), width=6)
    canvas.paste(pfp, (6, 6), pfp)
    return canvas

def create_welcome_card(u_id, u_first, u_username, c_name, u_pfp, c_pfp):
    try:
        # Load Background
        bg_path = "assets/wel2.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 600))
        else:
            bg = Image.new("RGBA", (1200, 600), (20, 20, 30))

        # Photo Processing (Standard size for frames)
        user_img = make_round(Image.open(u_pfp), (225, 225))
        chat_img = make_round(Image.open(c_pfp), (225, 225))

        # --- EXACT FRAME COORDINATES --- #
        # Left Side (Group Photo) - Placing inside Left Gold Frame
        bg.paste(chat_img, (135, 160), chat_img) 
        # Right Side (User Photo) - Placing inside Right Gold Frame
        bg.paste(user_img, (840, 160), user_img) 

        # Compact Panel at Bottom
        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Rounded box - width reduced to look slim
        draw_ov.rounded_rectangle((360, 440, 840, 560), radius=25, fill=(0, 0, 0, 180))
        bg = Image.alpha_composite(bg, overlay)

        # Typography
        try:
            f_title = ImageFont.truetype("assets/font.ttf", 45) # Welcome text size
            f_group = ImageFont.truetype("assets/font.ttf", 60) # Group Name size (Bigger)
            f_info = ImageFont.truetype("assets/font.ttf", 30)  # Details size
        except:
            f_title = f_group = f_info = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)

        # 1. "WELCOME TO" Text
        draw.text((600, 130), "WELCOME TO", font=f_title, fill=(255, 255, 255), anchor="mm")
        
        # 2. GROUP NAME (Centered & Bold Cyan)
        # Clean special chars that PIL can't render
        clean_c_name = re.sub(r'[^\x00-\x7F]+', '', c_name) or "GROUP"
        draw.text((600, 195), f"{clean_c_name[:15].upper()}", font=f_group, fill=(0, 255, 255), anchor="mm")

        # 3. USER DETAILS in Panel
        clean_u_name = re.sub(r'[^\x00-\x7F]+', '', u_first) or "User"
        draw.text((390, 455), f"NAME: {clean_u_name[:15]}", font=f_info, fill=(255, 255, 255))
        draw.text((390, 488), f"ID: {u_id}", font=f_info, fill=(0, 255, 255))
        draw.text((390, 521), f"USER: {u_username[:15]}", font=f_info, fill=(255, 255, 255))

        out = f"downloads/w_{u_id}.png"
        bg.save(out)
        return out
    except Exception as e:
        print(f"Error: {e}")
        return None

# --- Pyrogram Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
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
            member.chat.id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
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
