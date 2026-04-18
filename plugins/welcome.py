import asyncio
import os
import time
from datetime import datetime
import pytz
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
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

# --- High-End Image Logic --- #

def make_round(pfp, size=(300, 300)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    output = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    
    # Border & Glow
    border_size = (size[0] + 20, size[1] + 20)
    canvas = Image.new("RGBA", border_size, (0, 0, 0, 0))
    draw_can = ImageDraw.Draw(canvas)
    # Outer Glow Effect
    for i in range(10):
        draw_can.ellipse((i, i, border_size[0]-i, border_size[1]-i), outline=(255, 255, 255, 50 - i*5), width=2)
    
    canvas.paste(output, (10, 10), output)
    return canvas

def create_welcome_card(u_id, u_first, u_username, c_name, u_pfp):
    try:
        # Background Setup
        bg_path = "assets/wel2.png" # Make sure this is a high-res 1200x700 image
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 700))
        else:
            bg = Image.new("RGBA", (1200, 700), (15, 15, 25))

        # Time & Date Logic (IST)
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        join_time = now.strftime("%I:%M %p")
        join_date = now.strftime("%d %b, %Y")
        join_day = now.strftime("%A")

        # Process User Image
        user_img = make_round(Image.open(u_pfp), (320, 320))
        
        # Center PFP
        bg.paste(user_img, (440, 60), user_img)

        # Glassmorphism Text Box (Blurry transparent box)
        overlay = Image.new("RGBA", (1200, 700), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Main info box
        draw_ov.rounded_rectangle((80, 420, 1120, 660), radius=40, fill=(0, 0, 0, 180))
        # Side Badge for Date
        draw_ov.rounded_rectangle((900, 50, 1150, 150), radius=20, fill=(255, 255, 255, 30))
        
        bg = Image.alpha_composite(bg, overlay)

        # Fonts
        try:
            f_huge = ImageFont.truetype("assets/font.ttf", 80) # Welcome
            f_name = ImageFont.truetype("assets/font.ttf", 60) # User Name
            f_info = ImageFont.truetype("assets/font.ttf", 35) # Details
            f_date = ImageFont.truetype("assets/font.ttf", 30) # Date/Time
        except:
            f_huge = f_name = f_info = f_date = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)

        # Draw Text
        # "WELCOME" Text with a subtle Shadow
        draw.text((600, 480), "WELCOME", font=f_huge, fill=(0, 190, 255), anchor="mm")
        
        # User Name
        draw.text((600, 555), f"{u_first[:18]}", font=f_name, fill=(255, 255, 255), anchor="mm")
        
        # ID & Username Line
        info_text = f"ID: {u_id}  •  @{u_username if u_username != 'No Username' else 'N/A'}"
        draw.text((600, 615), info_text, font=f_info, fill=(200, 200, 200), anchor="mm")

        # Group Name (Top Left)
        draw.text((50, 50), f"TO: {c_name[:25].upper()}", font=f_date, fill=(255, 255, 255, 150))

        # Date & Time (Top Right Badge)
        draw.text((1025, 80), f"{join_time}", font=f_date, fill=(0, 255, 200), anchor="mm")
        draw.text((1025, 120), f"{join_date}", font=f_date, fill=(255, 255, 255), anchor="mm")

        out = f"downloads/welcome_{u_id}.png"
        bg.save(out, "PNG", quality=100)
        return out
    except Exception as e:
        print(f"Image Error: {e}")
        return None

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
    
    # User Profile Pic
    if user.photo:
        u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png")
    else:
        u_p = "assets/nodp.png" # Make sure this default image exists

    u_username = user.username if user.username else "No Username"
    
    loop = asyncio.get_running_loop()
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, member.chat.title, u_p)

    if card:
        caption = (
            f"<b>✨ ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴊᴏɪɴᴇᴅ ✨</b>\n\n"
            f"<b>┏━━━━━━━━━━━━━━━━━┓</b>\n"
            f"<b>┣👤 ɴᴀᴍᴇ :</b> {user.mention}\n"
            f"<b>┣🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>┣🔗 ᴜsᴇʀɴᴀᴍᴇ :</b> @{u_username}\n"
            f"<b>┣👥 ᴛᴏᴛᴀʟ ᴍᴇᴍʙᴇʀs :</b> <code>{count}</code>\n"
            f"<b>┗━━━━━━━━━━━━━━━━━┛</b>\n\n"
            f"✨ <i>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <b>{member.chat.title}</b>! ʜᴀᴠᴇ ᴀ ᴘʟᴇᴀsᴀɴᴛ sᴛᴀʏ.</i>"
        )
        
        await app.send_photo(
            chat_id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        # Cleanup
        for f in [card, u_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                try: os.remove(f)
                except: pass

@app.on_message(filters.command("wem") & ~filters.private)
async def welcome_toggle(_, m):
    try:
        user = await app.get_chat_member(m.chat.id, m.from_user.id)
        if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await m.reply_text("❌ <i>You must be an admin to use this.</i>")
    except: return

    if len(m.command) < 2:
        return await m.reply_text("<b>Configuration:</b>\n`/wem on` - Enable Welcome Card\n`/wem off` - Disable Welcome Card")
    
    state = m.command[1].lower()
    if state in ["on", "enable"]:
        await set_welcome_status(m.chat.id, "on")
        await m.reply_text("✅ <b>Welcome greeting enabled in this chat!</b>")
    elif state in ["off", "disable"]:
        await set_welcome_status(m.chat.id, "off")
        await m.reply_text("🔕 <b>Welcome greeting disabled in this chat!</b>")

__MODULE__ = "Welcome"
__HELP__ = """
**Premium Welcome Card**
/wem [on/off] - Toggle the welcome card for this group.

**Note:** Ensure I have admin rights to send messages and download profile pictures.
"""
