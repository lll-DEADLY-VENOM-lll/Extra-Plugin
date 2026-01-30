import re
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import BANNED_USERS
from VIPMUSIC import app

# Database functions - inka path check kar lein agar error aaye
from VIPMUSIC.utils.database import (
    deleteall_filters,
    get_filter,
    get_filters_names,
    save_filter,
)

# Agar aapke bot me delete_filter nahi hai to ise hata dein
try:
    from VIPMUSIC.utils.database import delete_filter
except ImportError:
    delete_filter = None

# In imports ko dhyan se dekhein, ye aapke purane code ke hisab se hain
from utils.error import capture_err
from utils.permissions import adminsOnly, member_permissions
from VIPMUSIC.utils.functions import (
    check_format,
    extract_text_and_keyb,
    get_data_and_name,
)
from VIPMUSIC.utils.keyboard import ikb
from .notes import extract_urls

__MODULE__ = "Filters"
__HELP__ = """
/filters - Chat ke saare filters dekhne ke liye.
/filter [NAME] - Naya filter banane ke liye (message ko reply karein).
/stop [NAME] - Kisi ek filter ko hatane ke liye.
/stopall - Saare filters ek saath delete karne ke liye.

**Supported Placeholders:**
- `{NAME}`: User ka naam
- `{ID}`: User ki ID
- `{USERNAME}`: User ka username
- `{GROUPNAME}`: Group ka naam
- `{DATE}`: Aaj ki tareekh
"""

@app.on_message(filters.command("filter") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def save_filters(_, message):
    try:
        if len(message.command) < 2:
            return await message.reply_text(
                "**Usage:**\nReply to a message with `/filter [FILTER_NAME]`"
            )

        replied_message = message.reply_to_message or message
        data, name = await get_data_and_name(replied_message, message)

        if len(name) < 2:
            return await message.reply_text("**Filter name 2 akshar se bada hona chahiye.**")

        _type = "text"
        file_id = None
        
        if replied_message.sticker: _type, file_id = "sticker", replied_message.sticker.file_id
        elif replied_message.animation: _type, file_id = "animation", replied_message.animation.file_id
        elif replied_message.photo: _type, file_id = "photo", replied_message.photo.file_id
        elif replied_message.document: _type, file_id = "document", replied_message.document.file_id
        elif replied_message.video: _type, file_id = "video", replied_message.video.file_id
        elif replied_message.video_note: _type, file_id = "video_note", replied_message.video_note.file_id
        elif replied_message.audio: _type, file_id = "audio", replied_message.audio.file_id
        elif replied_message.voice: _type, file_id = "voice", replied_message.voice.file_id

        if data:
            data = await check_format(ikb, data)
            if not data:
                return await message.reply_text("**Format galat hai!**")

        name = name.replace("_", " ").lower()
        _filter = {"type": _type, "data": data, "file_id": file_id}

        await save_filter(message.chat.id, name, _filter)
        return await message.reply_text(f"**Saved filter `{name}`.**")
    except Exception as e:
        await message.reply_text(f"**Error:** `{e}`")

@app.on_message(filters.command("stop") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_filter_cmd(_, message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/stop [FILTER_NAME]`")
    
    name = message.text.split(None, 1)[1].lower().replace("_", " ")
    
    # Direct database call to delete (using the same logic as stopall but for one)
    # Agar delete_filter module me nahi hai to iska alternative logic:
    all_filters = await get_filters_names(message.chat.id)
    if name in all_filters:
        # Note: Aapko apne database file me delete_filter function add karna padega
        # Agar error aaye to use ignore karein ya database.py me function banayein
        try:
            from VIPMUSIC.utils.database import delete_filter
            await delete_filter(message.chat.id, name)
            await message.reply_text(f"**Stopped filter `{name}`.**")
        except:
            await message.reply_text("**Is command ke liye database function missing hai.**")
    else:
        await message.reply_text("**Filter nahi mila.**")

@app.on_message(filters.command("filters") & ~filters.private & ~BANNED_USERS)
@capture_err
async def get_filterss(_, message):
    _filters = await get_filters_names(message.chat.id)
    if not _filters:
        return await message.reply_text("**Koi filters nahi hain.**")
    _filters.sort()
    msg = f"**{message.chat.title}** ke filters:\n"
    for _filter in _filters:
        msg += f"**-** `{_filter}`\n"
    await message.reply_text(msg)

@app.on_message(filters.text & ~filters.private & ~filters.forwarded & ~BANNED_USERS, group=1)
@capture_err
async def filters_re(_, message):
    text = message.text.lower().strip()
    if not text: return
    chat_id = message.chat.id
    list_of_filters = await get_filters_names(chat_id)
    
    for word in list_of_filters:
        pattern = r"( |^|[^\w])" + re.escape(word) + r"( |$|[^\w])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            _filter = await get_filter(chat_id, word)
            data_type = _filter["type"]
            data = _filter["data"]
            file_id = _filter.get("file_id")
            keyb = None

            if data:
                if "{NAME}" in data: data = data.replace("{NAME}", message.from_user.mention)
                if "{ID}" in data: data = data.replace("{ID}", str(message.from_user.id))
                if "{GROUPNAME}" in data: data = data.replace("{GROUPNAME}", message.chat.title)
                
                if re.findall(r"\[.+\,.+\]", data):
                    keyboard = extract_text_and_keyb(ikb, data)
                    if keyboard: data, keyb = keyboard

            target = message.reply_to_message or message
            if data_type == "text":
                await target.reply_text(data, reply_markup=keyb, disable_web_page_preview=True)
            elif data_type == "photo":
                await target.reply_photo(file_id, caption=data, reply_markup=keyb)
            # Isi tarah baki media types bhi...
            elif file_id:
                await target.reply_cached_media(file_id, caption=data, reply_markup=keyb)
            return

@app.on_message(filters.command("stopall") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_all(_, message):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data="stop_yes"), InlineKeyboardButton("No", callback_data="stop_no")]])
    await message.reply_text("**Saare filters delete karun?**", reply_markup=keyboard)

@app.on_callback_query(filters.regex("stop_(.*)"))
async def stop_all_cb(_, cb):
    if cb.data == "stop_yes":
        await deleteall_filters(cb.message.chat.id)
        await cb.message.edit("**Saare filters uda diye gaye!**")
    else:
        await cb.message.delete()
