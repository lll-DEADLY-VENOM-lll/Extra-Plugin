import re
import time
from pyrogram import filters
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from VIPMUSIC import app
from VIPMUSIC.utils.afkdb import add_afk, is_afk, remove_afk
from VIPMUSIC.utils.readable_time import get_readable_time

@app.on_message(filters.command(["afk", "brb"], prefixes=["/", "!"]))
async def active_afk(_, message: Message):
    if message.sender_chat:
        return
    user_id = message.from_user.id
    verifier, reasondb = await is_afk(user_id)
    
    if verifier:
        await remove_afk(user_id)
        try:
            afktype = reasondb["type"]
            timeafk = reasondb["time"]
            data = reasondb["data"]
            reasonafk = reasondb["reason"]
            seenago = get_readable_time((int(time.time() - timeafk)))
            if afktype == "text":
                await message.reply_text(f"**{message.from_user.first_name}** ɪs ʙᴀᴄᴋ ᴏɴʟɪɴᴇ ᴀɴᴅ ᴡᴀs ᴀᴡᴀʏ ғᴏʀ {seenago}")
            elif afktype == "text_reason":
                await message.reply_text(f"**{message.from_user.first_name}** ɪs ʙᴀᴄᴋ ᴏɴʟɪɴᴇ ᴀɴᴅ ᴡᴀs ᴀᴡᴀʏ ғᴏʀ {seenago}\n\nʀᴇᴀsᴏɴ: `{reasonafk}`")
            elif afktype == "animation":
                caption = f"**{message.from_user.first_name}** ɪs ʙᴀᴄᴋ ᴏɴʟɪɴᴇ ᴀɴᴅ ᴡᴀs ᴀᴡᴀʏ ғᴏʀ {seenago}"
                if str(reasonafk) != "None": caption += f"\n\nʀᴇᴀsᴏɴ: `{reasonafk}`"
                await message.reply_animation(data, caption=caption)
            elif afktype == "photo":
                caption = f"**{message.from_user.first_name}** ɪs ʙᴀᴄᴋ ᴏɴʟɪɴᴇ ᴀɴᴅ ᴡᴀs ᴀᴡᴀʏ ғᴏʀ {seenago}"
                if str(reasonafk) != "None": caption += f"\n\nʀᴇᴀsᴏɴ: `{reasonafk}`"
                await message.reply_photo(photo=f"downloads/{user_id}.jpg", caption=caption)
        except Exception:
            await message.reply_text(f"**{message.from_user.first_name}** ɪs ʙᴀᴄᴋ ᴏɴʟɪɴᴇ")

    # AFK sᴇᴛᴛɪɴɢ ʟᴏɢɪᴄ
    if len(message.command) == 1 and not message.reply_to_message:
        details = {"type": "text", "time": time.time(), "data": None, "reason": None}
    elif len(message.command) > 1 and not message.reply_to_message:
        _reason = (message.text.split(None, 1)[1].strip())[:100]
        details = {"type": "text_reason", "time": time.time(), "data": None, "reason": _reason}
    elif len(message.command) == 1 and message.reply_to_message and message.reply_to_message.animation:
        details = {"type": "animation", "time": time.time(), "data": message.reply_to_message.animation.file_id, "reason": None}
    elif len(message.command) > 1 and message.reply_to_message and message.reply_to_message.animation:
        _reason = (message.text.split(None, 1)[1].strip())[:100]
        details = {"type": "animation", "time": time.time(), "data": message.reply_to_message.animation.file_id, "reason": _reason}
    elif len(message.command) == 1 and message.reply_to_message and message.reply_to_message.photo:
        await app.download_media(message.reply_to_message, file_name=f"{user_id}.jpg")
        details = {"type": "photo", "time": time.time(), "data": None, "reason": None}
    elif len(message.command) > 1 and message.reply_to_message and message.reply_to_message.photo:
        await app.download_media(message.reply_to_message, file_name=f"{user_id}.jpg")
        _reason = message.text.split(None, 1)[1].strip()
        details = {"type": "photo", "time": time.time(), "data": None, "reason": _reason}
    elif message.reply_to_message and message.reply_to_message.sticker:
        if message.reply_to_message.sticker.is_animated:
            details = {"type": "text", "time": time.time(), "data": None, "reason": None}
        else:
            await app.download_media(message.reply_to_message, file_name=f"{user_id}.jpg")
            _reason = (message.text.split(None, 1)[1].strip())[:100] if len(message.command) > 1 else None
            details = {"type": "photo", "time": time.time(), "data": None, "reason": _reason}
    else:
        details = {"type": "text", "time": time.time(), "data": None, "reason": None}

    await add_afk(user_id, details)
    await message.reply_text(f"{message.from_user.first_name} ɪs ɴᴏᴡ ᴀғᴋ!")

chat_watcher_group = 1

@app.on_message(~filters.me & ~filters.bot & ~filters.via_bot, group=chat_watcher_group)
async def chat_watcher_func(_, message):
    if message.sender_chat or not message.from_user:
        return
    userid = message.from_user.id
    user_name = message.from_user.first_name
    
    # Check if sender is AFK
    verifier, reasondb = await is_afk(userid)
    if verifier:
        await remove_afk(userid)
        await message.reply_text(f"**{user_name}** ɪs ʙᴀᴄᴋ ᴏɴʟɪɴᴇ!")

    # Check for mentions
    msg = ""
    replied_user_id = 0
    if message.reply_to_message and message.reply_to_message.from_user:
        replied_first_name = message.reply_to_message.from_user.first_name
        replied_user_id = message.reply_to_message.from_user.id
        ver, db = await is_afk(replied_user_id)
        if ver:
            seenago = get_readable_time((int(time.time() - db['time'])))
            msg += f"**{replied_first_name}** ɪs ᴀғᴋ sɪɴᴄᴇ {seenago}\nʀᴇᴀsᴏɴ: `{db['reason']}`\n\n"

    if message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.MENTION:
                user_text = (message.text or message.caption)[entity.offset:entity.offset+entity.length]
                try:
                    user = await app.get_users(user_text)
                    if user.id == replied_user_id: continue
                    ver, db = await is_afk(user.id)
                    if ver:
                        seenago = get_readable_time((int(time.time() - db['time'])))
                        msg += f"**{user.first_name}** ɪs ᴀғᴋ sɪɴᴄᴇ {seenago}\nʀᴇᴀsᴏɴ: `{db['reason']}`\n\n"
                except: continue
            elif entity.type == MessageEntityType.TEXT_MENTION:
                user = entity.user
                if user.id == replied_user_id: continue
                ver, db = await is_afk(user.id)
                if ver:
                    seenago = get_readable_time((int(time.time() - db['time'])))
                    msg += f"**{user.first_name}** ɪs ᴀғᴋ sɪɴᴄᴇ {seenago}\nʀᴇᴀsᴏɴ: `{db['reason']}`\n\n"

    if msg:
        await message.reply_text(msg)

__MODULE__ = "AFK"
__HELP__ = """
**AFK Cᴏᴍᴍᴀɴᴅ**
/afk [reason] - Sᴇᴛ AFK sᴛᴀᴛᴜs.
/brb - sᴀᴍᴇ ᴀs /afk.
"""
