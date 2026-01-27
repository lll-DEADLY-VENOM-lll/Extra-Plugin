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
            # अगर इमेज नहीं है तो डार्क बैकग्राउंड ताकि सफेद टेक्स्ट दिखे
            bg = Image.new("RGBA", (1200, 600), (15, 15, 25))

        # Photo Processing
        user_img = make_round(Image.open(u_pfp), (225, 225))
        chat_img = make_round(Image.open(c_pfp), (225, 225))

        # Paste Photos
        bg.paste(chat_img, (135, 160), chat_img) 
        bg.paste(user_img, (840, 160), user_img) 

        # Bottom Panel
        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle((360, 440, 840, 560), radius=25, fill=(0, 0, 0, 180))
        bg = Image.alpha_composite(bg, overlay)

        # Typography
        try:
            f_title = ImageFont.truetype("assets/font.ttf", 50)
            f_group = ImageFont.truetype("assets/font.ttf", 55)
            f_info = ImageFont.truetype("assets/font.ttf", 30)
        except:
            f_title = f_group = f_info = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)

        # 1. "WELCOME TO" (रंग Cyan रखा है ताकि सफेद पर भी दिखे)
        draw.text((600, 100), "WELCOME TO", font=f_title, fill=(0, 255, 255), anchor="mm")
        
        # 2. GROUP NAME (Regex हटा दिया ताकि पूरा नाम आए)
        # सिर्फ इमोजी हटाने के लिए हल्का फिल्टर
        clean_c_name = c_name[:20] if c_name else "GROUP"
        draw.text((600, 180), f"{clean_c_name.upper()}", font=f_group, fill=(255, 255, 255), anchor="mm")

        # 3. USER DETAILS
        clean_u_name = u_first[:15] if u_first else "User"
        draw.text((390, 455), f"NAME: {clean_u_name}", font=f_info, fill=(255, 255, 255))
        draw.text((390, 488), f"ID: {u_id}", font=f_info, fill=(0, 255, 255))
        draw.text((390, 521), f"USER: {u_username[:15]}", font=f_info, fill=(255, 255, 255))

        out = f"downloads/w_{u_id}.png"
        bg.save(out)
        return out
    except Exception as e:
        print(f"Error in create_welcome_card: {e}")
        return None

# --- Pyrogram Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
async def member_join_handler(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    if await get_welcome_status(member.chat.id) == "off":
        return

    user = member.new_chat_member.user
    u_username = f"@{user.username}" if user.username else "No Username"
    
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"
    c_p = await app.download_media(member.chat.photo.big_file_id, f"c{member.chat.id}.png") if member.chat.photo else "assets/nodp.png"

    loop = asyncio.get_running_loop()
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, member.chat.title, u_p, c_p)

    if card:
        caption = (
            f"◦•●◉✿ ᴡᴇʟᴄᴏᴍᴇ ʙᴀʙʏ ✿◉●•◦\n"
            f"▰▱▱▱▱▱▱▱▱▱▱▱▱▱▰\n\n"
            f"● ɴᴀᴍᴇ ➥ {user.mention}\n"
            f"● ᴜsᴇʀɴᴀᴍᴇ ➥ {u_username}\n"
            f"● ᴜsᴇʀ ɪᴅ ➥ <code>{user.id}</code>\n\n"
            f"❖ ᴘᴏᴡᴇʀᴇᴅ ʙʏ ➥ <a href='https://t.me/{app.username}'>{app.name}</a>\n"
            f"▰▱▱▱▱▱▱▱▱▱▱▱▱▱▰"
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
