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

# --- Database Setup --- #
welcomedb = MongoClient(MONGO_DB_URI)
status_db = welcomedb.welcome_status_db.status

async def get_welcome_status(chat_id):
    status = status_db.find_one({"chat_id": chat_id})
    return status.get("welcome", "on") if status else "on"

# --- Robust API Fetcher (Multi-Source) --- #

async def get_anime_wallpaper():
    """Fail-safe API: Agar ek fail ho to dusri chalegi"""
    urls = [
        "https://nekos.best/api/v2/wallpaper",
        "https://waifu.pics/api/sfw/waifu",
        "https://nekos.best/api/v2/waifu"
    ]
    random.shuffle(urls)
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Key check based on API source
                        if 'results' in data:
                            return data['results'][0]['url']
                        elif 'url' in data:
                            return data['url']
            except:
                continue
    return "https://wallpaperaccess.com/full/1311152.jpg" # Super Fallback

async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return Image.open(BytesIO(await resp.read())).convert("RGBA")

# --- Pro Image Engine --- #

def create_pro_banner(bg_img, pfp_img, u_id, u_name, u_user, count, c_title):
    W, H = 1200, 600
    # Background processing
    bg = bg_img.resize((W, H), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Darken overlay
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.7)

    # 1. Right Side Glass Panel
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    # Futuristic Slanted Box
    draw_ov.polygon([(400, 0), (W, 0), (W, H), (300, H)], fill=(0, 0, 0, 180))
    # Neon Glow Line
    draw_ov.line([(400, 0), (300, H)], fill=(0, 255, 255, 255), width=5)
    
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # 2. PFP Spotlight (Left Side)
    pfp = pfp_img.resize((350, 350), Image.Resampling.LANCZOS)
    mask = Image.new("L", (350, 350), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 350, 350), fill=255)
    pfp.putalpha(mask)
    
    # Outer Glow for PFP
    draw.ellipse((40, 115, 410, 485), outline=(0, 255, 255, 150), width=15)
    bg.paste(pfp, (50, 125), pfp)

    # 3. Smart Fonts (Unicode / Symbol Fix)
    def load_font(size):
        # Multiple font paths for reliability
        paths = ["assets/font.ttf", "assets/bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arial.ttf"]
        for p in paths:
            if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    f_large = load_font(90)
    f_name = load_font(60)
    f_small = load_font(30)

    # Clean stylish names to avoid boxes ❎
    clean_name = re.sub(r'[^\x00-\x7F]+', ' ', u_name).strip() or "User"
    clean_title = re.sub(r'[^\x00-\x7F]+', ' ', c_title).strip() or "Server"

    # 4. Content Placement
    # Welcome Header
    draw.text((480, 100), "WELCOME", font=f_large, fill=(0, 255, 255))
    
    # User Name (Pinkish/White Highlight)
    draw.text((480, 210), clean_name[:15].upper(), font=f_name, fill=(255, 255, 255))
    
    # Info list
    draw.line((480, 300, 1100, 300), fill=(255, 255, 255, 100), width=2)
    draw.text((480, 330), f"🆔 ID: {u_id}", font=f_small, fill=(200, 200, 200))
    draw.text((480, 380), f"🌐 USER: @{u_user}", font=f_small, fill=(200, 200, 200))
    
    # Rank Badge (Bottom Right)
    draw.rounded_rectangle((480, 450, 850, 530), radius=20, fill=(255, 20, 147, 180))
    draw.text((510, 465), f"RANKED #{count}", font=f_name, fill=(255, 255, 255))

    # Server Info (Top Left)
    tz = pytz.timezone('Asia/Kolkata')
    time_str = datetime.now(tz).strftime("%I:%M %p")
    draw.text((50, 40), f"📍 {clean_title[:25]}", font=f_small, fill=(255, 255, 255, 180))
    draw.text((1050, 40), time_str, font=f_small, fill=(0, 255, 255))

    path = f"downloads/card_{u_id}.png"
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
        # Automatic Multi-API Image Fetch
        bg_url = await get_anime_wallpaper()
        bg_img = await download_image(bg_url)
        
        # User PFP
        if user.photo:
            pfp_path = await app.download_media(user.photo.big_file_id)
            pfp_img = Image.open(pfp_path)
        else:
            pfp_img = Image.new("RGBA", (350, 350), (20, 20, 40))
            pfp_path = None

        u_username = user.username if user.username else "No_Username"

        # Generate Poster
        loop = asyncio.get_running_loop()
        card = await loop.run_in_executor(None, create_pro_banner, bg_img, pfp_img, user.id, user.first_name, u_username, count, member.chat.title)

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

# ... (Command /wem code)
