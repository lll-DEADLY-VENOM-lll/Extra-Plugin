import asyncio
import os
import random
import aiohttp
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

# --- Automatic Asset Fetcher --- #

async def fetch_random_anime_img():
    """API se random anime image ka URL nikalne ke liye"""
    urls = [
        "https://nekos.best/api/v2/waifu",
        "https://nekos.best/api/v2/husbando",
        "https://waifu.pics/api/sfw/waifu"
    ]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(random.choice(urls)) as resp:
                data = await resp.json()
                # Nekos.best aur Waifu.pics ka JSON structure thoda alag hota hai
                return data['results'][0]['url'] if 'results' in data else data['url']
    except:
        return "https://wallpaperaccess.com/full/1311152.jpg" # Fallback link

async def get_image_from_url(url):
    """URL se image download karke PIL object banane ke liye"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return Image.open(BytesIO(await resp.read())).convert("RGBA")

# --- Pro Image Engine --- #

def create_dynamic_card(bg_img, pfp_img, u_id, u_name, u_user, count, c_title):
    # 1. Canvas Setup
    width, height = 1200, 700
    bg = bg_img.resize((width, height), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
    
    # Darken Background for readability
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.6)
    
    # 2. Glassmorphism Panel
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    draw_ov.rounded_rectangle((50, 50, 1150, 650), radius=50, fill=(0, 0, 0, 140), outline=(255, 255, 255, 30), width=2)
    bg = Image.alpha_composite(bg, overlay)
    
    # 3. Profile Picture (Circle)
    pfp = pfp_img.resize((300, 300), Image.Resampling.LANCZOS)
    mask = Image.new("L", (300, 300), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 300, 300), fill=255)
    
    circular_pfp = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
    circular_pfp.putalpha(mask)
    
    # PFP Glow
    pfp_border = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
    ImageDraw.Draw(pfp_border).ellipse((0, 0, 320, 320), outline=(0, 255, 255, 180), width=10)
    bg.paste(pfp_border, (90, 190), pfp_border)
    bg.paste(circular_pfp, (100, 200), circular_pfp)

    # 4. Automatic Font Selector
    def load_font(size):
        # Try finding any stylish system font automatically
        font_names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "Verdana.ttf"]
        for f in font_names:
            try: return ImageFont.truetype(f, size)
            except: continue
        return ImageFont.load_default()

    f_huge = load_font(100)
    f_mid = load_font(60)
    f_small = load_font(35)
    
    draw = ImageDraw.Draw(bg)
    
    # 5. Dynamic Text Drawing
    # Neon Welcome
    draw.text((450, 140), "WELCOME", font=f_huge, fill=(0, 255, 255))
    
    # Name & User Info
    draw.text((450, 260), u_name[:15].upper(), font=f_mid, fill=(255, 255, 255))
    draw.line((450, 350, 1050, 350), fill=(255, 255, 255, 100), width=3)
    
    draw.text((450, 380), f"ID: {u_id}", font=f_small, fill=(200, 200, 200))
    draw.text((450, 430), f"USER: @{u_user}", font=f_small, fill=(200, 200, 200))
    
    # Badge
    draw.rounded_rectangle((450, 500, 900, 580), radius=20, fill=(255, 20, 147, 100))
    draw.text((480, 515), f"MEMBER RANK #{count}", font=f_small, fill=(255, 255, 255))

    # Server/Time Info
    tz = pytz.timezone('Asia/Kolkata')
    curr_time = datetime.now(tz).strftime("%I:%M %p")
    draw.text((80, 70), f"SERVER: {c_title[:20].upper()}", font=f_small, fill=(255, 255, 255, 150))
    draw.text((950, 70), curr_time, font=f_small, fill=(0, 255, 255))

    temp_path = f"downloads/auto_{u_id}.png"
    bg.save(temp_path)
    return temp_path

# --- Bot Handler --- #

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
        # 1. Automatic Background Fetching
        anime_url = await fetch_random_anime_img()
        bg_img = await get_image_from_url(anime_url)
        
        # 2. User PFP Fetching
        if user.photo:
            pfp_path = await app.download_media(user.photo.big_file_id)
            pfp_img = Image.open(pfp_path)
        else:
            pfp_img = Image.new("RGB", (300, 300), (30, 30, 50))
            pfp_path = None

        u_username = user.username if user.username else "No_Username"

        # 3. Generate Card
        loop = asyncio.get_running_loop()
        card_path = await loop.run_in_executor(None, create_dynamic_card, bg_img, pfp_img, user.id, user.first_name, u_username, count, member.chat.title)

        # 4. Send with stylish caption
        caption = (
            f"<b>🌸 ᴀᴜᴛᴏ-ɢᴇɴᴇʀᴀᴛᴇᴅ ᴡᴇʟᴄᴏᴍᴇ 🌸</b>\n\n"
            f"<b>╔══════════════════╗</b>\n"
            f"<b>   👤 ɴᴀᴍᴇ :</b> {user.mention}\n"
            f"<b>   🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>   📊 ʀᴀɴᴋ :</b> <code>#{count}</code>\n"
            f"<b>╚══════════════════╝</b>\n\n"
            f"<i>🚀 ᴇɴᴊᴏʏ ʏᴏᴜʀ sᴛᴀʏ ɪɴ {member.chat.title}!</i>"
        )

        await app.send_photo(
            chat_id, 
            photo=card_path, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        # Cleanup
        if os.path.exists(card_path): os.remove(card_path)
        if pfp_path and os.path.exists(pfp_path): os.remove(pfp_path)

    except Exception as e:
        print(f"Automatic Error: {e}")

# ... (Keep /wem command same)
