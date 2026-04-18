import asyncio
import os
import random
from datetime import datetime
import pytz
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
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

# --- Advanced Image Engine (No Background Required) --- #

def generate_gradient_bg(size=(1200, 700)):
    """Background image ki zarurat nahi, yeh khud gradient banayega."""
    base = Image.new("RGB", size, (20, 20, 30))
    top_color = (random.randint(40, 80), 0, random.randint(100, 200)) # Deep Purple/Blue
    bottom_color = (0, random.randint(100, 150), random.randint(150, 255)) # Cyan
    
    draw = ImageDraw.Draw(base)
    for y in range(size[1]):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (y / size[1]))
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (y / size[1]))
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (y / size[1]))
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    
    # Add some abstract "Vibe" (Random circles/lines)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    for _ in range(10):
        x, y = random.randint(0, 1200), random.randint(0, 700)
        r = random.randint(50, 200)
        o_draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 255, 255, random.randint(5, 15)))
    
    return Image.alpha_composite(base.convert("RGBA"), overlay)

def get_hexagon_pfp(pfp_path, size=(320, 320)):
    """User ki photo ko Hexagon shape mein convert karne ke liye."""
    img = Image.open(pfp_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Draw Hexagon
    coords = []
    import math
    for i in range(6):
        angle = math.radians(i * 60)
        x = size[0]/2 + (size[0]/2) * math.cos(angle)
        y = size[1]/2 + (size[1]/2) * math.sin(angle)
        coords.append((x, y))
    draw.polygon(coords, fill=255)
    
    output = Image.new("RGBA", size, (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)
    
    # Border with Glow
    border = Image.new("RGBA", (size[0]+20, size[1]+20), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border)
    b_coords = [(x+10, y+10) for x, y in coords]
    for i in range(10, 0, -1):
        b_draw.polygon(b_coords, outline=(0, 255, 255, 100 - i*10), width=i*2)
    
    border.paste(output, (10, 10), output)
    return border

def create_ultra_card(u_id, u_name, u_user, c_title, count, pfp_path):
    # 1. Background Generation
    bg = generate_gradient_bg()
    draw = ImageDraw.Draw(bg)
    
    # 2. Hexagon PFP
    pfp = get_hexagon_pfp(pfp_path)
    bg.paste(pfp, (80, 180), pfp)

    # 3. Fonts
    try:
        font_path = "assets/font.ttf"
        f_wel = ImageFont.truetype(font_path, 100) # Big Welcome
        f_name = ImageFont.truetype(font_path, 70)  # Name
        f_sub = ImageFont.truetype(font_path, 35)   # Details
    except:
        f_wel = f_name = f_sub = ImageFont.load_default()

    # 4. Glass Effect Box for text
    overlay = Image.new("RGBA", (1200, 700), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    o_draw.rounded_rectangle((450, 150, 1150, 550), radius=40, fill=(255, 255, 255, 20), outline=(255, 255, 255, 50), width=3)
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg) # Redraw on composite

    # 5. Stylish Text
    # Welcome Label
    draw.text((490, 180), "WELCOME", font=f_wel, fill=(0, 255, 255))
    
    # User Name with Shadow
    draw.text((493, 293), u_name[:15].upper(), font=f_name, fill=(0, 0, 0, 100)) # Shadow
    draw.text((490, 290), u_name[:15].upper(), font=f_name, fill=(255, 255, 255))
    
    # Divider line
    draw.line((490, 380, 1100, 380), fill=(255, 255, 255, 100), width=2)

    # Info Details
    draw.text((490, 410), f"ID : {u_id}", font=f_sub, fill=(200, 200, 200))
    draw.text((490, 460), f"USER : @{u_user}", font=f_sub, fill=(200, 200, 200))
    draw.text((490, 510), f"RANK : #{count} MEMBER", font=f_sub, fill=(255, 215, 0)) # Gold Color

    # Top Header
    tz = pytz.timezone('Asia/Kolkata')
    time_now = datetime.now(tz).strftime("%I:%M %p | %d %b")
    draw.text((50, 50), f"SERVER: {c_title[:30].upper()}", font=f_sub, fill=(255, 255, 255, 150))
    draw.text((950, 50), time_now, font=f_sub, fill=(255, 255, 255, 150))

    out_path = f"downloads/pro_card_{u_id}.png"
    bg.save(out_path, quality=100)
    return out_path

# --- Pyrogram Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
async def member_join_handler(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    count = await app.get_chat_members_count(chat_id)
    
    # User PFP
    if user.photo:
        pfp_file = await app.download_media(user.photo.big_file_id, f"pfp_{user.id}.png")
    else:
        pfp_file = "assets/nodp.png" # Create a simple blue image if not exists

    u_username = user.username if user.username else "NO_USER"
    
    loop = asyncio.get_running_loop()
    try:
        card = await loop.run_in_executor(None, create_ultra_card, user.id, user.first_name, u_username, member.chat.title, count, pfp_file)
        
        caption = (
            f"<b>✨ ᴘʀᴇᴍɪᴜᴍ ᴡᴇʟᴄᴏᴍᴇ ✨</b>\n\n"
            f"<b>👤 ɴᴀᴍᴇ :</b> {user.mention}\n"
            f"<b>🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>📊 ʀᴀɴᴋ :</b> <code>#{count}</code>\n\n"
            f"<i>🚀 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {member.chat.title}! ᴋᴇᴇᴘ ᴛʜᴇ ᴄʜᴀᴛ ᴀʟɪᴠᴇ.</i>"
        )

        await app.send_photo(
            chat_id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'card' in locals() and os.path.exists(card): os.remove(card)
        if "assets/" not in pfp_file and os.path.exists(pfp_file): os.remove(pfp_file)

@app.on_message(filters.command("wem") & ~filters.private)
async def welcome_toggle(_, m):
    # Same permission logic as before
    if len(m.command) < 2:
        return await m.reply_text("<b>Usage:</b> `/wem on` | `/wem off`")
    
    state = m.command[1].lower()
    if state in ["on", "enable"]:
        await set_welcome_status(m.chat.id, "on")
        await m.reply_text("✨ <b>Ultra Welcome Enabled!</b>")
    elif state in ["off", "disable"]:
        await set_welcome_status(m.chat.id, "off")
        await m.reply_text("🌑 <b>Welcome Disabled!</b>")
