import asyncio
import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps
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

# --- High-Resolution Image Logic --- #

def make_round(pfp_path, size=(520, 520)):
    """Creates a massive circular PFP with a thick black border."""
    try:
        pfp = Image.open(pfp_path).convert("RGBA")
        pfp = pfp.resize(size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        output = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        
        # Canvas for the border
        border_size = (size[0] + 40, size[1] + 40)
        canvas = Image.new("RGBA", border_size, (0, 0, 0, 0))
        draw_can = ImageDraw.Draw(canvas)
        # Extra thick black border (width=20)
        draw_can.ellipse((0, 0, border_size[0]-5, border_size[1]-5), outline="black", width=20)
        canvas.paste(output, (20, 20), output)
        return canvas
    except:
        return None

def create_welcome_card(u_id, u_first, u_username, u_pfp_path):
    try:
        # 1. Load your white background image
        bg_path = "assets/white_bg.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1280, 720))
        else:
            bg = Image.new("RGBA", (1280, 720), (255, 255, 255))

        draw = ImageDraw.Draw(bg)
        
        # 2. MASSIVE FONT SIZES
        try:
            f_welcome = ImageFont.truetype("assets/cursive.ttf", 300) # Giant Welcome
            f_details = ImageFont.truetype("assets/font.ttf", 110)    # Massive Details
            f_footer = ImageFont.truetype("assets/font.ttf", 60)      # Clear Footer
        except:
            f_welcome = f_details = f_footer = ImageFont.load_default()

        # 3. Draw Text (Color: Pure Black)
        # "Welcome" text (Top Left)
        draw.text((80, 40), "Welcome", font=f_welcome, fill="black")

        # User ID and Username (Center Left)
        draw.text((100, 380), f"ID : {u_id}", font=f_details, fill="black")
        draw.text((100, 500), f"USERNAME : {u_username}", font=f_details, fill="black")

        # Footer at the bottom
        draw.text((640, 640), "THANKS FOR JOINING US", font=f_footer, fill="black", anchor="mm")
        
        # Thick decorative line at bottom center
        draw.line((400, 680, 880, 680), fill="black", width=12)
        draw.ellipse((625, 665, 655, 695), fill="black") # Decorative dot

        # 4. Paste Massive Profile Picture (Right Side)
        pfp_circular = make_round(u_pfp_path, (520, 520))
        if pfp_circular:
            # Shifted right to fill the space
            bg.paste(pfp_circular, (680, 50), pfp_circular)

        output_path = f"downloads/welcome_{u_id}.png"
        bg.save(output_path)
        return output_path
    except Exception as e:
        print(f"Drawing Error: {e}")
        return None

# --- Pyrogram Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
async def member_join_handler(_, member: ChatMemberUpdated):
    if not (member.new_chat_member and not member.old_chat_member):
        return
    if await get_welcome_status(member.chat.id) == "off":
        return

    user = member.new_chat_member.user
    bot = await app.get_me()
    u_username = f"@{user.username}" if user.username else "None"
    
    if user.photo:
        u_pfp_path = await app.download_media(user.photo.big_file_id, f"u{user.id}.png")
    else:
        u_pfp_path = "assets/nodp.png"

    loop = asyncio.get_running_loop()
    welcome_img = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, u_pfp_path)

    if welcome_img:
        caption = (
            f"ㅤㅤㅤㅤ◦•●◉✿ ᴡᴇʟᴄᴏᴍᴇ ʙᴀʙʏ ✿◉●•◦\n"
            f"▰▱▱▱▱▱▱▱▱▱▱▱▱▱▰\n\n"
            f"● ɴᴀᴍᴇ ➥ {user.mention}\n"
            f"● ᴜsᴇʀɴᴀᴍᴇ ➥ {u_username}\n"
            f"● ᴜsᴇʀ ɪᴅ ➥ <code>{user.id}</code>\n\n"
            f"❖ ᴘᴏᴡᴇʀᴇᴅ ʙʏ ➥ <a href='https://t.me/{bot.username}'>{bot.first_name}</a>\n"
            f"▰▱▱▱▱▱▱▱▱▱▱▱▱▱▰"
        )
        
        await app.send_photo(
            member.chat.id, 
            photo=welcome_img, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{bot.username}?startgroup=true")]
            ])
        )

        if os.path.exists(welcome_img): os.remove(welcome_img)
        if u_pfp_path and os.path.exists(u_pfp_path) and "assets/" not in u_pfp_path: os.remove(u_pfp_path)

@app.on_message(filters.command("welcome") & ~filters.private)
async def welcome_toggle(_, m):
    user_member = await app.get_chat_member(m.chat.id, m.from_user.id)
    if user_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return
    if len(m.command) < 2: return await m.reply_text("Usage: /welcome on|off")
    choice = m.command[1].lower()
    await set_welcome_status(m.chat.id, choice)
    await m.reply_text(f"✅ Welcome message turned **{choice.upper()}**")

__MODULE__ = "Welcome"
