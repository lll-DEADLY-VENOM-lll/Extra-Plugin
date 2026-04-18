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

# --- 101% Automatic Font Downloader --- #
FONT_PATH = "assets/elite_font.ttf"
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

async def download_assets():
    if not os.path.exists("assets"):
        os.makedirs("assets")
    if not os.path.exists(FONT_PATH):
        async with aiohttp.ClientSession() as session:
            async with session.get(FONT_URL) as resp:
                if resp.status == 200:
                    with open(FONT_PATH, "wb") as f:
                        f.write(await resp.read())

# --- Robust Image Logic --- #

async def get_anime_bg():
    urls = ["https://nekos.best/api/v2/wallpaper", "https://waifu.pics/api/sfw/waifu"]
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(random.choice(urls)) as resp:
                data = await resp.json()
                return data['results'][0]['url'] if 'results' in data else data['url']
        except:
            return "https://wallpaperaccess.com/full/1311152.jpg"

async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return Image.open(BytesIO(await resp.read())).convert("RGBA")

def create_god_banner(bg_img, pfp_img, u_id, u_name, u_user, count, c_title):
    W, H = 1200, 600
    bg = bg_img.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=2))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)

    # 1. Overlay Design
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    # Slanted futuristic cut
    draw_ov.polygon([(450, 0), (W, 0), (W, H), (350, H)], fill=(0, 0, 0, 200))
    draw_ov.line([(450, 0), (350, H)], fill=(255, 0, 255, 255), width=8) # Pink Neon Line
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # 2. PFP with Neon Ring
    pfp = pfp_img.resize((350, 350), Image.Resampling.LANCZOS)
    mask = Image.new("L", (350, 350), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 350, 350), fill=255)
    pfp.putalpha(mask)
    
    # Dual Tone Ring
    draw.ellipse((40, 115, 410, 485), outline=(0, 255, 255, 255), width=12)
    bg.paste(pfp, (50, 125), pfp)

    # 3. Font Logic
    try:
        f_huge = ImageFont.truetype(FONT_PATH, 100)
        f_name = ImageFont.truetype(FONT_PATH, 70)
        f_small = ImageFont.truetype(FONT_PATH, 35)
    except:
        f_huge = f_name = f_small = ImageFont.load_default()

    # Smart Text Cleaning (Empty name handle)
    u_name = re.sub(r'[^\x20-\x7E]+', '', u_name).strip()
    if not u_name: u_name = "User"
    c_title = re.sub(r'[^\x20-\x7E]+', '', c_title).strip() or "Server"

    # 4. Text Placement
    draw.text((490, 100), "WELCOME", font=f_huge, fill=(0, 255, 255))
    draw.text((490, 210), f" {u_name[:15].upper()} ", font=f_name, fill=(255, 255, 255))
    
    # Divider
    draw.rectangle((490, 310, 1100, 312), fill=(255, 255, 255, 80))
    
    # Info
    draw.text((490, 340), f"ID: {u_id}", font=f_small, fill=(200, 200, 200))
    draw.text((490, 390), f"USER: @{u_user}", font=f_small, fill=(200, 200, 200))
    
    # Member Rank Badge
    draw.rounded_rectangle((490, 460, 850, 540), radius=20, fill=(255, 0, 150, 180))
    draw.text((520, 475), f"MEMBER #{count}", font=f_small, fill=(255, 255, 255))

    # Server Info
    tz = pytz.timezone('Asia/Kolkata')
    time_str = datetime.now(tz).strftime("%I:%M %p")
    draw.text((50, 40), f"SERVER: {c_title[:20]}", font=f_small, fill=(255, 255, 255))
    draw.text((1000, 40), time_str, font=f_small, fill=(0, 255, 255))

    path = f"downloads/final_{u_id}.png"
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
        # Automatic Setup Check
        await download_assets()
        
        # Async Fetching
        bg_url = await get_anime_bg()
        bg_img, pfp_raw = await asyncio.gather(download_image(bg_url), app.download_media(user.photo.big_file_id) if user.photo else asyncio.sleep(0))
        
        pfp_img = Image.open(pfp_raw) if pfp_raw else Image.new("RGBA", (350, 350), (20, 20, 40))

        u_username = user.username if user.username else "No_Username"

        # Image Creation
        loop = asyncio.get_running_loop()
        card = await loop.run_in_executor(None, create_god_banner, bg_img, pfp_img, user.id, user.first_name, u_username, count, member.chat.title)

        await app.send_photo(
            chat_id, 
            photo=card, 
            caption=f"<b>✨ ɴᴇᴡ ᴍᴇᴍʙᴇʀ sʏsᴛᴇᴍ ᴇɴᴛʀʏ ✨</b>\n\n<b>👤 ɴᴀᴍᴇ :</b> {user.mention}\n<b>🆔 ɪᴅ :</b> <code>{user.id}</code>\n<b>📊 ʀᴀɴᴋ :</b> <code>#{count}</code>\n\n<b>🚀 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {member.chat.title}!</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        if os.path.exists(card): os.remove(card)
        if pfp_raw and os.path.exists(pfp_raw): os.remove(pfp_raw)

    except Exception as e:
        print(f"Final Error: {e}")
