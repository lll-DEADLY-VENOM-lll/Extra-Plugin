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

def make_round(pfp, size=(250, 250)):
    pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    pfp.putalpha(mask)
    
    canvas = Image.new("RGBA", (size[0]+16, size[1]+16), (0, 0, 0, 0))
    draw_can = ImageDraw.Draw(canvas)
    draw_can.ellipse((0, 0, size[0]+16, size[1]+16), outline=(255, 255, 255, 255), width=8)
    canvas.paste(pfp, (8, 8), pfp)
    return canvas

def create_welcome_card(u_id, u_first, u_username, c_name, u_pfp, c_pfp):
    try:
        bg_path = "assets/wel2.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 600))
        else:
            bg = Image.new("RGBA", (1200, 600), (10, 10, 15))

        user_img = make_round(Image.open(u_pfp), (240, 240))
        chat_img = make_round(Image.open(c_pfp), (180, 180))

        bg.paste(chat_img, (60, 60), chat_img) 
        bg.paste(user_img, (480, 80), user_img) 

        overlay = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle((100, 380, 1100, 560), radius=30, fill=(0, 0, 0, 160))
        bg = Image.alpha_composite(bg, overlay)

        try:
            f_main = ImageFont.truetype("assets/font.ttf", 65)
            f_sub = ImageFont.truetype("assets/font.ttf", 40)
            f_id = ImageFont.truetype("assets/font.ttf", 30)
        except:
            f_main = f_sub = f_id = ImageFont.load_default()

        draw = ImageDraw.Draw(bg)
        welcome_text = f"WELCOME TO {c_name[:20].upper()}"
        draw.text((600, 420), welcome_text, font=f_sub, fill=(0, 220, 255), anchor="mm")
        draw.text((600, 480), f"{u_first[:15]}", font=f_main, fill=(255, 255, 255), anchor="mm")
        draw.text((600, 530), f"ID: {u_id}  |  USER: {u_username[:20]}", font=f_id, fill=(200, 200, 200), anchor="mm")

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
    
    chat_id = member.chat.id
    if await get_welcome_status(chat_id) == "off":
        return

    user = member.new_chat_member.user
    u_username = f"@{user.username}" if user.username else "No Username"
    
    u_p = await app.download_media(user.photo.big_file_id, f"u{user.id}.png") if user.photo else "assets/nodp.png"
    c_p = await app.download_media(member.chat.photo.big_file_id, f"c{chat_id}.png") if member.chat.photo else "assets/nodp.png"

    loop = asyncio.get_running_loop()
    card = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, member.chat.title, u_p, c_p)

    if card:
        caption = (
            f"<b>🎉 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀᴛ!</b>\n\n"
            f"<b>👤 ɴᴀᴍᴇ :</b> {user.mention}\n"
            f"<b>🆔 ɪᴅ :</b> <code>{user.id}</code>\n"
            f"<b>🔗 ᴜsᴇʀɴᴀᴍᴇ :</b> {u_username}\n\n"
            f"✨ <i>ʜᴀᴠᴇ ᴀ ɢʀᴇᴀᴛ ᴛɪᴍᴇ ʜᴇʀᴇ!</i>"
        )
        
        await app.send_photo(
            chat_id, 
            photo=card, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        for f in [card, u_p, c_p]:
            if f and os.path.exists(f) and "assets/" not in f:
                os.remove(f)

# --- Updated Command: /wem --- #

@app.on_message(filters.command("wem") & ~filters.private)
async def welcome_toggle(_, m):
    try:
        user = await app.get_chat_member(m.chat.id, m.from_user.id)
        if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await m.reply_text("❌ You don't have permission to use this command.")
    except:
        return

    if len(m.command) < 2:
        return await m.reply_text("<b>Usage:</b>\n`/wem on` - Enable Welcome\n`/wem off` - Disable Welcome")
    
    state = m.command[1].lower()
    if state in ["on", "enable", "yes"]:
        await set_welcome_status(m.chat.id, "on")
        await m.reply_text("✅ <b>Welcome message has been enabled!</b>")
    elif state in ["off", "disable", "no"]:
        await set_welcome_status(m.chat.id, "off")
        await m.reply_text("🔕 <b>Welcome message has been disabled!</b>")
    else:
        await m.reply_text("❌ Invalid argument. Use `on` or `off`.")

__MODULE__ = "Welcome"
__HELP__ = """
/wem [on/off] - Enable or Disable the premium welcome card in your group.

**Note:** Bot must be an Admin to work properly.
"""
