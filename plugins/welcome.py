import asyncio
import os
from PIL import Image, ImageDraw, ImageFont
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

# --- Improved Image Logic --- #

def make_round(pfp, size=(340, 340)):
    """User photo ko perfect round shape dene ke liye"""
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    return pfp

def create_welcome_card(u_id, u_first, u_username, u_pfp):
    try:
        # 1. Background loading (Aapki neon brick wali image)
        bg_path = "assets/wel2.png" 
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA")
        else:
            bg = Image.new("RGBA", (1280, 853), (20, 20, 30))

        # Background size ko fix rakhein coordinates maintain karne ke liye
        bg = bg.resize((1280, 853))

        # 2. User Photo Processing
        # Photo size thoda badha diya hai taaki neon circle ke fit aaye
        user_img = make_round(Image.open(u_pfp), (340, 340))
        
        # PFP ko neon circle ke center mein paste karna
        # Coordinates ko niche shift kiya gaya hai (235 tak)
        bg.paste(user_img, (26, 235), user_img) 

        # 3. Fonts Setup
        try:
            # Font size 50-55 is good for visibility
            f_data = ImageFont.truetype("assets/font.ttf", 55)
        except:
            f_data = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)

        # 4. Dynamic Text Placement
        # Image par likhe "NAME", "ID" aur "USERNAME" ke samne text adjust kiya hai
        text_color = (255, 255, 255) # Pure White neon look ke liye
        
        name_val = u_first[:15] if u_first else "User"
        uname_val = u_username[:15] if u_username != "None" else "No Username"

        # Coordinates for fixed labels on the image
        draw.text((635, 530), f": {name_val}", font=f_data, fill=text_color)
        draw.text((545, 655), f": {u_id}", font=f_data, fill=text_color)
        draw.text((775, 780), f": {uname_val}", font=f_data, fill=text_color)

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
    u_username = f"@{user.username}" if user.username else "None"
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"

    loop = asyncio.get_running_loop()
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, u_p)

    if card:
        caption = (
            f"✨ <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ɢʀᴏᴜᴘ!</b> ✨\n\n"
            f"👤 <b>ɴᴀᴍᴇ:</b> {user.mention}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user.id}</code>\n"
            f"🔗 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {u_username}\n\n"
            f"Enjoy your stay here!"
        )
        
        await app.send_photo(
            member.chat.id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        for f in [card, u_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                os.remove(f)

@app.on_message(filters.command("welcome") & ~filters.private)
async def welcome_toggle(_, m):
    # Check if admin
    user = await app.get_chat_member(m.chat.id, m.from_user.id)
    if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return
    if len(m.command) < 2: return
    state = m.command[1].lower()
    if state in ["on", "off"]:
        await set_welcome_status(m.chat.id, state)
        await m.reply_text(f"✅ Welcome message turned {state.upper()}")

__MODULE__ = "Welcome"
