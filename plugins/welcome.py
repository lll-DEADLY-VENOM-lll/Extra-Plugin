import asyncio
import os
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

def make_round(pfp, size=(320, 320)):
    """User ki photo ko gol (round) karne ke liye"""
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    return pfp

def create_welcome_card(u_id, u_first, u_username, u_pfp):
    try:
        # 1. Load Background (Jo photo aapne di hai)
        bg_path = "assets/wel2.png" 
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA")
        else:
            # Fallback agar image missing ho
            bg = Image.new("RGBA", (1280, 853), (20, 20, 30))

        # Background size fix (1280x853 default for this template)
        bg = bg.resize((1280, 853))

        # 2. User Photo Processing
        # Circle ka size aur position image ke glowing circle ke hisaab se
        user_img = make_round(Image.open(u_pfp), (315, 315))
        
        # Paste User Photo inside the neon circle
        # Position (x, y) coordinates for the orange circle in your image
        bg.paste(user_img, (38, 178), user_img) 

        # 3. Typography (Fonts)
        try:
            # Neon style ke liye koi bold font use karein
            font_path = "assets/font.ttf"
            f_data = ImageFont.truetype(font_path, 45)
        except:
            f_data = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)

        # 4. Adding Dynamic Text
        # Name, ID aur Username labels ke aage values likhna
        # Pinkish-White color neon effect ke liye
        text_color = (255, 255, 255) 
        
        clean_u_name = u_first[:20] if u_first else "User"
        
        # Coordinates image ke labels "NAME", "ID", "USERNAME" ke samne set kiye hain
        draw.text((615, 545), f": {clean_u_name}", font=f_data, fill=text_color)
        draw.text((540, 672), f": {u_id}", font=f_data, fill=text_color)
        draw.text((750, 795), f": {u_username[:20]}", font=f_data, fill=text_color)

        out = f"downloads/welcome_{u_id}.png"
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
    u_username = f"@{user.username}" if user.username else "None"
    
    # Download User PFP
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"

    loop = asyncio.get_running_loop()
    # Image creation process
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, u_p)

    if card:
        caption = (
            f"✨ <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ɢʀᴏᴜᴘ!</b> ✨\n\n"
            f"👤 <b>ɴᴀᴍᴇ:</b> {user.mention}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user.id}</code>\n"
            f"🔗 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {u_username}\n\n"
            f"Hope you have a great time here!"
        )
        
        await app.send_photo(
            member.chat.id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        # Clean up files
        for f in [card, u_p]:
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
    await m.reply_text(f"✅ Welcome message has been turned {state.upper()}")

__MODULE__ = "Welcome"
