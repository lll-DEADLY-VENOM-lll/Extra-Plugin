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
    # Default to "on" if no status is found
    return status.get("welcome", "on") if status else "on"

async def set_welcome_status(chat_id, state):
    status_db.update_one({"chat_id": chat_id}, {"$set": {"welcome": state}}, upsert=True)

# --- Image Generation Logic --- #

def make_round(pfp_path, size=(400, 400)):
    """Creates a circular profile picture with a thick black border."""
    try:
        pfp = Image.open(pfp_path).convert("RGBA")
        pfp = pfp.resize(size, Image.Resampling.LANCZOS)
        
        # Create circular mask
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        
        # Apply mask
        output = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        
        # Create a slightly larger canvas for the black border
        border_size = (size[0] + 20, size[1] + 20)
        canvas = Image.new("RGBA", border_size, (0, 0, 0, 0))
        draw_can = ImageDraw.Draw(canvas)
        
        # Draw the thick black circle border
        draw_can.ellipse((0, 0, border_size[0]-2, border_size[1]-2), outline="black", width=12)
        
        # Paste the circular PFP into the border canvas
        canvas.paste(output, (10, 10), output)
        return canvas
    except Exception as e:
        print(f"Error making round PFP: {e}")
        return None

def create_welcome_card(u_id, u_first, u_username, u_pfp_path):
    try:
        # 1. Load the White Background
        bg_path = "assets/white_bg.png"
        if os.path.exists(bg_path):
            bg = Image.open(bg_path).convert("RGBA").resize((1200, 675))
        else:
            # Fallback to plain white if image is missing
            bg = Image.new("RGBA", (1200, 675), (255, 255, 255))

        draw = ImageDraw.Draw(bg)
        
        # 2. Load Fonts
        try:
            f_welcome = ImageFont.truetype("assets/cursive.ttf", 150) # Cursive for 'Welcome'
            f_details = ImageFont.truetype("assets/font.ttf", 65)     # Regular for ID/User
            f_footer = ImageFont.truetype("assets/font.ttf", 45)      # Smaller for Footer
        except:
            f_welcome = f_details = f_footer = ImageFont.load_default()

        # 3. Draw Text (Color: Black)
        # "Welcome" text at top left
        draw.text((100, 60), "Welcome", font=f_welcome, fill="black")

        # User details at center left
        draw.text((100, 380), f"ID : {u_id}", font=f_details, fill="black")
        draw.text((100, 470), f"USERNAME : {u_username}", font=f_details, fill="black")

        # Footer text at bottom center
        draw.text((600, 600), "THANKS FOR JOINING US", font=f_footer, fill="black", anchor="mm")
        
        # 4. Draw Decorative Line & Dot
        draw.line((380, 635, 820, 635), fill="black", width=4)
        draw.ellipse((592, 627, 608, 643), fill="black") # Small center dot

        # 5. Process and Paste Profile Picture
        pfp_circular = make_round(u_pfp_path, (380, 380))
        if pfp_circular:
            bg.paste(pfp_circular, (720, 160), pfp_circular)

        # 6. Save final image
        output_path = f"downloads/welcome_{u_id}.png"
        bg.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error creating welcome card: {e}")
        return None

# --- Pyrogram Handlers --- #

@app.on_chat_member_updated(filters.group, group=10)
async def member_join_handler(_, member: ChatMemberUpdated):
    # Only trigger for new members joining
    if not (member.new_chat_member and not member.old_chat_member):
        return
    
    # Check if welcome is turned off for this chat
    if await get_welcome_status(member.chat.id) == "off":
        return

    user = member.new_chat_member.user
    
    # Get bot details for "Powered By" and buttons
    bot = await app.get_me()
    
    # Handle username
    u_username = f"@{user.username}" if user.username else "None"
    
    # Download User PFP or use default
    if user.photo:
        u_pfp_path = await app.download_media(user.photo.big_file_id, f"u{user.id}.png")
    else:
        u_pfp_path = "assets/nodp.png"

    # Generate the image in a background thread
    loop = asyncio.get_running_loop()
    welcome_img = await loop.run_in_executor(None, create_welcome_card, user.id, user.first_name, u_username, u_pfp_path)

    if welcome_img:
        # Decorative Caption Style
        caption = (
            f"ㅤㅤㅤㅤ◦•●◉✿ ᴡᴇʟᴄᴏᴍᴇ ʙᴀʙʏ ✿◉●•◦\n"
            f"▰▱▱▱▱▱▱▱▱▱▱▱▱▱▰\n\n"
            f"● ɴᴀᴍᴇ ➥ {user.mention}\n"
            f"● ᴜsᴇʀɴᴀᴍᴇ ➥ {u_username}\n"
            f"● ᴜsᴇʀ ɪᴅ ➥ <code>{user.id}</code>\n\n"
            f"❖ ᴘᴏᴡᴇʀᴇᴅ ʙʏ ➥ <a href='https://t.me/{bot.username}'>{bot.first_name}</a>\n"
            f"▰▱▱▱▱▱▱▱▱▱▱▱▱▱▰"
        )
        
        # Send the photo
        await app.send_photo(
            member.chat.id, 
            photo=welcome_img, 
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{bot.username}?startgroup=true")]
            ])
        )

        # Cleanup: Delete temporary files to save space
        if os.path.exists(welcome_img):
            os.remove(welcome_img)
        if os.path.exists(u_pfp_path) and "assets/" not in u_pfp_path:
            os.remove(u_pfp_path)

@app.on_message(filters.command("welcome") & ~filters.private)
async def welcome_toggle(_, m):
    # Check if the user is an admin
    user_member = await app.get_chat_member(m.chat.id, m.from_user.id)
    if user_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return
    
    # Check for command arguments (on/off)
    if len(m.command) < 2: 
        return await m.reply_text("Usage: /welcome on | /welcome off")
    
    choice = m.command[1].lower()
    if choice in ["on", "off"]:
        await set_welcome_status(m.chat.id, choice)
        await m.reply_text(f"✅ Welcome message has been turned **{choice.upper()}**")
    else:
        await m.reply_text("Please use 'on' or 'off'.")

__MODULE__ = "Welcome"
__HELP__ = "/welcome [on/off] - Toggle the welcome image for new members."
