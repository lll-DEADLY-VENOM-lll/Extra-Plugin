import os
import random
import requests
import pytz
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from telegraph import upload_file
from motor.motor_asyncio import AsyncIOMotorClient

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatType

# VIPMUSIC se app import karein
from VIPMUSIC import app

# --- CONFIGURATION (MongoDB Setup) ---
MONGO_URL = "mongodb+srv://your_mongodb_url" # <--- Apni MongoDB URL yahan dalen
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["CouplesDB"]
history_col = db["couple_history"] 
daily_col = db["daily_couples"]    

# --- HELPERS ---

def get_today_date():
    return datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%d/%m/%Y")

def get_tomorrow_date():
    tomorrow = datetime.now(pytz.timezone("Asia/Kolkata")) + timedelta(days=1)
    return tomorrow.strftime("%d/%m/%Y")

async def is_already_paired(cid, u1, u2):
    pair = sorted([u1, u2])
    found = await history_col.find_one({"chat_id": cid, "pair": pair})
    return True if found else False

async def save_pair_to_history(cid, u1, u2):
    pair = sorted([u1, u2])
    await history_col.update_one(
        {"chat_id": cid, "pair": pair},
        {"$set": {"chat_id": cid, "pair": pair}},
        upsert=True
    )

def download_image(url, path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, "wb") as f:
            f.write(response.content)
    return path

# --- MAIN COMMAND LOGIC ---

@app.on_message(filters.command(["couple", "couples"]))
async def couple_handler(_, message):
    cid = message.chat.id
    
    # Check if the command is used in Group
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ Tʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ ɢʀᴏᴜᴘs.")

    today = get_today_date()
    tomorrow = get_tomorrow_date()
    
    # Temp file paths (using cid to prevent conflicts)
    p1_path = f"downloads/pfp_{cid}.png"
    p2_path = f"downloads/pfp1_{cid}.png"
    test_image_path = f"downloads/test_{cid}.png"
    cppic_path = f"downloads/cppic_{cid}.png"

    try:
        user1, user2 = None, None
        is_manual = False

        # --- COMMAND USAGE LOGIC ---
        
        # 1. Agar user ne galat arguments diye (e.g., /couple @user1)
        if len(message.command) == 2:
            return await message.reply_text(
                "**💡 HOW TO USE COUPLE COMMAND:**\n\n"
                "1️⃣ **Automatic:** Type `/couple` (Daily 1 unique pair)\n"
                "2️⃣ **Manual:** Type `/couple @username1 @username2` (To create custom poster)\n\n"
                "Example: `/couple @Abhay @Nisha`"
            )

        # 2. MANUAL SELECTION (/couple @user1 @user2)
        elif len(message.command) == 3:
            is_manual = True
            m = await message.reply_text("❣️ Creating your Custom Couple poster...")
            try:
                user1 = await app.get_users(message.command[1])
                user2 = await app.get_users(message.command[2])
                if user1.id == user2.id:
                    return await m.edit("Ek hi insaan khud ka couple nahi ban sakta! 🗿")
            except Exception:
                return await m.edit("❌ Iɴᴠᴀʟɪᴅ Usᴇʀɴᴀᴍᴇ/ID. Make sure both users are in this group!")

        # 3. AUTOMATIC DAILY SELECTION
        else:
            # Check if already selected for today
            daily = await daily_col.find_one({"chat_id": cid, "date": today})
            if daily:
                m = await message.reply_text("❣️ Showing today's couple...")
                u1 = await app.get_users(daily["couple"]["c1_id"])
                u2 = await app.get_users(daily["couple"]["c2_id"])
                
                txt = f"**Tᴏᴅᴀʏ's ᴄᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ ᴅᴀʏ 🎉:\n\n{u1.mention} + {u2.mention} = ❣️\n\nNᴇxᴛ ᴄᴏᴜᴘʟᴇs ᴡɪʟʟ ʙᴇ sᴇʟᴇᴄᴛᴇᴅ ᴏɴ {tomorrow}!!**"
                await message.reply_photo(daily["img_url"], caption=txt)
                return await m.delete()

            # Fresh unique selection logic
            m = await message.reply_text("❣️ Finding a unique pair for today...")
            users = []
            async for member in app.get_chat_members(cid, limit=80):
                if not member.user.is_bot and not member.user.is_deleted:
                    users.append(member.user.id)

            if len(users) < 2:
                return await m.edit("Group mein kam se kam 2 log chahiye couple banane ke liye.")

            random.shuffle(users)
            found = False
            for i in range(len(users)):
                for j in range(i + 1, len(users)):
                    if not await is_already_paired(cid, users[i], users[j]):
                        user1 = await app.get_users(users[i])
                        user2 = await app.get_users(users[j])
                        found = True
                        break
                if found: break
            
            if not found: # Fallback if all pairs used
                ids = random.sample(users, 2)
                user1 = await app.get_users(ids[0])
                user2 = await app.get_users(ids[1])

        # --- IMAGE GENERATION (Dono cases ke liye same) ---
        
        # PFPs download karein
        for u, path in [(user1, p1_path), (user2, p2_path)]:
            try:
                await app.download_media(u.photo.big_file_id, file_name=path)
            except:
                download_image("https://telegra.ph/file/05aa686cf52fc666184bf.jpg", path)
        
        # Background
        bg_url = "https://telegra.ph/file/96f36504f149e5680741a.jpg"
        download_image(bg_url, cppic_path)
        
        # Pillow process
        img1 = Image.open(p1_path).resize((437, 437))
        img2 = Image.open(p2_path).resize((437, 437))
        bg = Image.open(cppic_path)

        mask = Image.new("L", (437, 437), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 437, 437), fill=255)
        img1.putalpha(mask); img2.putalpha(mask)

        bg.paste(img1, (116, 160), img1)
        bg.paste(img2, (789, 160), img2)
        bg.save(test_image_path)

        # Upload & Send
        upload = upload_file(test_image_path)
        final_url = f"https://graph.org/{upload[0]}"

        title = "Cᴜsᴛᴏᴍ" if is_manual else "Tᴏᴅᴀʏ"
        caption = f"**{title}'s ᴄᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ ᴅᴀʏ 🎉:\n\n{user1.mention} + {user2.mention} = ❣️\n\nNᴇxᴛ ᴄᴏᴜᴘʟᴇs ᴡɪʟʟ ʙᴇ sᴇʟᴇᴄᴛᴇᴅ ᴏɴ {tomorrow}!!**"

        await message.reply_photo(
            final_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Aᴅᴅ ᴍᴇ 🌋", url=f"https://t.me/{app.username}?startgroup=true")]])
        )

        # Database updates
        await save_pair_to_history(cid, user1.id, user2.id)
        if not is_manual:
            await daily_col.update_one(
                {"chat_id": cid, "date": today},
                {"$set": {"couple": {"c1_id": user1.id, "c2_id": user2.id}, "img_url": final_url}},
                upsert=True
            )
        await m.delete()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        for f in [p1_path, p2_path, test_image_path, cppic_path]:
            if os.path.exists(f): os.remove(f)
