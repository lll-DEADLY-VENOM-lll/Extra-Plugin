from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pymongo import MongoClient
from VIPMUSIC import app
import asyncio
from VIPMUSIC.misc import SUDOERS
from config import MONGO_DB_URI
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import (
    ChatAdminRequired,
    UserNotParticipant,
    UsernameInvalid,
    PeerIdInvalid,
)

# Database Setup
fsubdb = MongoClient(MONGO_DB_URI)
forcesub_collection = fsubdb.status_db.status

# --- SET FORCE SUB COMMAND ---
@app.on_message(filters.command(["fsub", "forcesub"]) & filters.group)
async def set_forcesub(client: Client, message: Message):
    if not message.from_user: # Anonymous Admin Check
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if user is Admin or Sudo
    try:
        member = await client.get_chat_member(chat_id, user_id)
    except Exception:
        return

    if not (member.status.name in ["OWNER", "ADMINISTRATOR"] or user_id in SUDOERS):
        return await message.reply_text("**ᴏɴʟʏ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀs ᴏʀ sᴜᴅᴏᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.**")

    # Disable Fsub
    if len(message.command) == 2 and message.command[1].lower() in ["off", "disable"]:
        forcesub_collection.delete_one({"chat_id": chat_id})
        return await message.reply_text("**✅ ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ʙᴇᴇɴ ᴅɪsᴀʙʟᴇᴅ ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.**")

    if len(message.command) != 2:
        return await message.reply_text("**ᴜsᴀɢᴇ:**\n`/fsub @ChannelUsername`\n`/fsub -100123456789`\n`/fsub off` **ᴛᴏ ᴅɪsᴀʙʟᴇ**")

    channel_input = message.command[1]

    # Clean Input (Link ko username mein convert karna)
    if "t.me/" in channel_input:
        channel_input = channel_input.split("t.me/")[1]
    if channel_input.startswith("@"):
        channel_input = channel_input.replace("@", "")
    
    try:
        # Check if it's a Chat ID
        if channel_input.startswith("-100"):
            channel_input = int(channel_input)
    except ValueError:
        pass

    try:
        channel_info = await client.get_chat(channel_input)
        channel_id = channel_info.id
        channel_title = channel_info.title
        
        # Invite link generate karna
        try:
            channel_link = await app.export_chat_invite_link(channel_id)
        except:
            if channel_info.username:
                channel_link = f"https://t.me/{channel_info.username}"
            else:
                return await message.reply_text("**❌ ᴘʟᴇᴀsᴇ ᴍᴀᴋᴇ ᴍᴇ ᴀᴅᴍɪɴ ɪɴ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴡɪᴛʜ 'ɪɴᴠɪᴛᴇ ᴜsᴇʀs' ᴘᴇʀᴍɪssɪᴏɴ.**")

        channel_username = channel_info.username if channel_info.username else channel_id

        # Bot Admin check
        bot = await client.get_me()
        bot_is_admin = False
        async for admin in client.get_chat_members(channel_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if admin.user.id == bot.id:
                bot_is_admin = True
                break

        if not bot_is_admin:
            return await message.reply_text(f"**🚫 ɪ'ᴍ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ [{channel_title}]({channel_link})**\nᴘʟᴇᴀsᴇ ᴍᴀᴋᴇ ᴍᴇ ᴀᴅᴍɪɴ ᴛʜᴇʀᴇ ᴛᴏ ᴇɴᴀʙʟᴇ ғsᴜʙ.")

        # Save to DB
        forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"channel_id": channel_id, "channel_username": channel_username, "channel_title": channel_title, "channel_link": channel_link}},
            upsert=True
        )

        await message.reply_text(f"**✅ ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!**\n\n**ᴄʜᴀɴɴᴇʟ:** [{channel_title}]({channel_link})\n**ɪᴅ:** `{channel_id}`")

    except (UsernameInvalid, PeerIdInvalid):
        await message.reply_text("**❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɪᴅ. ᴘʟᴇᴀsᴇ ɢɪᴠᴇ ᴀ ᴠᴀʟɪᴅ ᴘᴜʙʟɪᴄ ᴄʜᴀɴɴᴇʟ.**")
    except Exception as e:
        await message.reply_text(f"**Error:** `{e}`")

# --- CHECK MEMBERSHIP FUNCTION ---
async def check_forcesub(client: Client, message: Message):
    if not message.from_user:
        return True

    chat_id = message.chat.id
    user_id = message.from_user.id

    if user_id in SUDOERS:
        return True

    forcesub_data = forcesub_collection.find_one({"chat_id": chat_id})
    if not forcesub_data:
        return True

    channel_id = forcesub_data["channel_id"]
    channel_link = forcesub_data.get("channel_link", "https://t.me/Telegram")

    try:
        await client.get_chat_member(channel_id, user_id)
        return True
    except UserNotParticipant:
        try:
            await message.delete()
        except:
            pass

        user_mention = message.from_user.mention
        await message.reply_photo(
            photo="https://envs.sh/Tn_.jpg",
            caption=f"**👋 ʜᴇʟʟᴏ {user_mention},**\n\n**ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛᴏ sᴇɴᴅ ᴍᴇssᴀɢᴇs ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("๏ ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ ๏", url=channel_link)]]),
        )
        return False
    except Exception:
        return True

# --- MESSAGE HANDLER ---
@app.on_message(filters.group & ~filters.bot, group=30)
async def enforce_forcesub(client: Client, message: Message):
    # Agar user member nahi hai, toh ye function aage execute nahi hone dega
    await check_forcesub(client, message)

@app.on_callback_query(filters.regex("close_force_sub"))
async def close_force_sub(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()

__MODULE__ = "ғsᴜʙ"
__HELP__ = """
/fsub @Username - ᴄʜᴀɴɴᴇʟ sᴇᴛ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ.
/fsub off - ғsᴜʙ ʙᴀɴᴅ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ.
"""
