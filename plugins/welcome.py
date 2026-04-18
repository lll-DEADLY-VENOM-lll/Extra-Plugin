import asyncio
import os
import random
import aiohttp
import re
from io import BytesIO
from datetime import datetime
import pytz
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
from pyrogram import enums, filters
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from VIPMUSIC import app
from config import MONGO_DB_URI

# --- Database --- #
welcomedb = MongoClient(MONGO_DB_URI)
status_db = welcomedb.welcome_status_db.status

async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

# --- Advanced Utils --- #

def clean_text(text):
    """Stylish symbols ko remove karne ke liye taki font ❎ na dikhaye"""
    return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()

async def get_anime_bg():
    """High Resolution Anime Wallpapers API"""
    url = "https://nekos.best/api/v2/wallpaper"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data['results'][0]['url']

async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return Image.open(BytesIO(await resp.read())).convert("RGBA")

# --- Pro Banner Engine --- #

def create_banner(bg_img, pfp_img, u_id, u_name, u_user, count, c_title):
    # 1. Canvas Dimensions (Cinema Style)
    W, H = 1200, 600
    bg = bg_img.resize((W, H), Image.Resampling.LANCZOS)
    
    # 2. Modern Overlay (Side Gradient)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    # Futuristic Slanted Panel
    draw_ov.polygon([(0, 0), (700, 0), (500, H), (0, H)], fill=(0, 0, 0, 200))
    # Accent line
    draw_ov.line([(700, 0), (500, H)], fill=(0, 255, 255, 255), width=8)
    
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # 3. User PFP (Circular with Double Stroke)
    pfp = pfp_img.resize((300, 300), Image.Resampling.LANCZOS)
    mask = Image.new("L", (300, 300), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 300, 300), fill=255)
    pfp.putalpha(mask)
    
    # PFP Border Glow
    draw.ellipse((45, 145, 355, 455), outline=(0, 255, 255, 255), width=10)
    bg.paste(pfp, (50, 150), pfp)

    # 4. Smart Font Loading (Fixes ❎ Boxes)
    def load_font(size):
        # List of system fonts that support more characters
        font_paths = [
            "assets/font.ttf", 
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arial.ttf"
        ]
        for path in font_paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    font_main = load_font(80)
    font_sub = load_font(40)
    font_info = load_font(30)

    # 5. Text Placement
    u_name = clean_text(u_name) if u_name else "User"
    c_title = clean_text(c_title)
    
    # "WELCOME" Text with Shadow
    draw.text((433, 103), "WELCOME", font=font_main, fill=(0, 0, 0, 150)) # Shadow
    draw.text((430, 100), "WELCOME", font=font_main, fill=(0, 255, 255))
    
    # Name
    draw.text((430, 200), f"{u_name[:15].upper()}", font=font_sub, fill=(255, 255, 255))
    
    # Info Box (Modern Look)
    draw.rectangle((430, 270, 900, 272), fill=(255, 255, 255, 100)) # Divider
    
    draw.text((430, 300), f"ID: {u_id}", font=font_info, fill=(200, 200, 200))
    draw.text((430, 350), f"USER: @{u_user}", font=font_info, fill=(200, 200, 200))
    
    # Rank Badge (Bottom Left)
    draw.rounded_rectangle((430, 420, 750, 490), radius=15, fill=(255, 0, 100, 200))
    draw.text((455, 435), f"RANK #{count}", font=font_sub, fill=(255, 255, 255))

    # Server Info
    tz = pytz.timezone('Asia/Kolkata')
    time_now = datetime.now(tz).strftime("%I:%M %p")
    draw.text((50, 40), f"📍 {c_title[:25]}", font=font_info, fill=(255, 255, 255))
    draw.text((1050, 40), time_now, font=font_info, fill=(0, 255, 255))

    path = f"downloads/banner_{u_id}.png"
    bg.save(path)
    return path

# --- Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
async def member_join_handler(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    count = await app.get_chat_members_count(chat_id)

    try:
        # Automatic Anime Wallpaper Fetch
        bg_url = await get_anime_bg()
        bg_img = await download_image(bg_url)
        
        # User PFP
        if user.photo:
            pfp_path = await app.download_media(user.photo.big_file_id)
            pfp_img = Image.open(pfp_path)
        else:
            pfp_img = Image.new("RGBA", (300, 300), (20, 20, 40))
            pfp_path = None

        u_username = user.username if user.username else "No_Username"

        # Generate Masterpiece
        loop = asyncio.get_running_loop()
        card = await loop.run_in_executor(None, create_banner, bg_img, pfp_img, user.id, user.first_name, u_username, count, member.chat.title)

        caption = (
            f"<b>🎌 ɴᴇᴡ ɴᴀᴋᴀᴍᴀ ᴀʀʀɪᴠᴇᴅ 🎌</b>\n\n"
            f"<b>👤 ɴᴀᴍᴇ :</b> {user.mention}\n"
            f"<b>🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>📊 ʀᴀɴᴋ :</b> <code>#{count}</code>\n\n"
            f"<i>🚀 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ sᴇʀᴠᴇʀ! ʜᴀᴠᴇ ᴀ ɢʀᴇᴀᴛ ᴛɪᴍᴇ.</i>"
        )

        await app.send_photo(
            chat_id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        if os.path.exists(card): os.remove(card)
        if pfp_path and os.path.exists(pfp_path): os.remove(pfp_path)

    except Exception as e:
        print(f"Error: {e}")

# ... (Command /wem remains same)
