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

# --- Robust Assets Downloader --- #
FONT_PATH = "assets/elite_font.ttf"
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

async def download_assets():
    if not os.path.exists("assets"):
        os.makedirs("assets")
    if not os.path.exists(FONT_PATH):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FONT_URL) as resp:
                    if resp.status == 200:
                        with open(FONT_PATH, "wb") as f:
                            f.write(await resp.read())
        except Exception as e:
            print(f"Font download failed: {e}")

# --- Safe Image Fetcher --- #

async def get_anime_url():
    """Returns a high-quality anime image URL with multi-source fallback"""
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
                        img_url = data['results'][0]['url'] if 'results' in data else data['url']
                        # Check if it's a valid image link
                        if img_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return img_url
            except:
                continue
    return "https://wallpaperaccess.com/full/1311152.jpg"

async def download_image(url):
    """Safely download and open image with error handling"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    img = Image.open(BytesIO(content)).convert("RGBA")
                    return img
    except Exception as e:
        print(f"Image Error for {url}: {e}")
    # Final Fallback Image (Pure Dark Blue)
    return Image.new("RGBA", (1200, 600), (10, 10, 30))

# --- Pro Engine --- #

def create_god_banner(bg_img, pfp_img, u_id, u_name, u_user, count, c_title):
    W, H = 1200, 600
    # Background
    bg = bg_img.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=2))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)

    # Slanted HUD Layout
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    draw_ov.polygon([(450, 0), (W, 0), (W, H), (350, H)], fill=(0, 0, 0, 210))
    draw_ov.line([(450, 0), (350, H)], fill=(0, 255, 255, 255), width=10)
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # Profile Pic
    pfp = pfp_img.resize((350, 350), Image.Resampling.LANCZOS)
    mask = Image.new("L", (350, 350), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 350, 350), fill=255)
    pfp.putalpha(mask)
    draw.ellipse((40, 115, 410, 485), outline=(255, 0, 255, 200), width=15)
    bg.paste(pfp, (50, 125), pfp)

    # Font handling
    try: font_large = ImageFont.truetype(FONT_PATH, 100)
    except: font_large = ImageFont.load_default()
    
    # Text Cleaning
    u_name = re.sub(r'[^\x20-\x7E]+', '', u_name).strip() or "User"
    c_title = re.sub(r'[^\x20-\x7E]+', '', c_title).strip() or "Server"

    draw.text((490, 100), "WELCOME", font=font_large, fill=(0, 255, 255))
    draw.text((490, 220), u_name[:15].upper(), font=ImageFont.truetype(FONT_PATH, 70) if os.path.exists(FONT_PATH) else font_large, fill=(255, 255, 255))
    
    draw.rectangle((490, 320, 1100, 322), fill=(255, 255, 255, 100))
    
    # Details
    f_info = ImageFont.truetype(FONT_PATH, 35) if os.path.exists(FONT_PATH) else font_large
    draw.text((490, 350), f"ID: {u_id}  |  RANK: #{count}", font=f_info, fill=(200, 200, 200))
    draw.text((490, 400), f"USER: @{u_user}", font=f_info, fill=(200, 200, 200))
    
    # Rank Badge
    draw.rounded_rectangle((490, 470, 850, 550), radius=20, fill=(255, 0, 150, 255))
    draw.text((535, 485), "NEW NAKAMA", font=f_info, fill=(255, 255, 255))

    path = f"downloads/final_{u_id}.png"
    bg.save(path)
    return path

# --- Handler --- #

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
        await download_assets()
        
        # Async Fetch
        bg_url = await get_anime_url()
        bg_img = await download_image(bg_url)
        
        if user.photo:
            pfp_path = await app.download_media(user.photo.big_file_id)
            pfp_img = Image.open(pfp_path).convert("RGBA")
        else:
            pfp_img = Image.new("RGBA", (350, 350), (20, 20, 40))
            pfp_path = None

        loop = asyncio.get_running_loop()
        card = await loop.run_in_executor(None, create_god_banner, bg_img, pfp_img, user.id, user.first_name, user.username or "N/A", count, member.chat.title)

        await app.send_photo(
            chat_id, 
            photo=card, 
            caption=f"<b>🌸 ɴᴇᴡ ɴᴀᴋᴀᴍᴀ ᴊᴏɪɴᴇᴅ 🌸</b>\n\n<b>👤 ɴᴀᴍᴇ :</b> {user.mention}\n<b>🆔 ɪᴅ :</b> <code>{user.id}</code>\n<b>📊 ʀᴀɴᴋ :</b> <code>#{count}</code>\n\n<b>🚀 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {member.chat.title}!</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        if os.path.exists(card): os.remove(card)
        if pfp_path and os.path.exists(pfp_path): os.remove(pfp_path)

    except Exception as e:
        print(f"Handler Error: {e}")
