import re
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import BANNED_USERS
from VIPMUSIC import app

# Database imports
from VIPMUSIC.utils.database import (
    deleteall_filters,
    get_filter,
    get_filters_names,
    save_filter,
)

# Delete filter check
try:
    from VIPMUSIC.utils.database import delete_filter
except ImportError:
    delete_filter = None

from utils.error import capture_err
from utils.permissions import adminsOnly
from VIPMUSIC.utils.functions import (
    check_format,
    extract_text_and_keyb,
    get_data_and_name,
)
from VIPMUSIC.utils.keyboard import ikb

__MODULE__ = "Filters"
__HELP__ = """
**Sirf Groups ke liye:**

/filters - Chat ke saare filters dekhne ke liye.
/filter [NAME] - Naya filter banane ke liye (Kisi message, sticker ya video ko reply karein).
/stop [NAME] - Kisi filter ko hatane ke liye.
/stopall - Saare filters delete karne ke liye.

**Placeholders:**
- `{NAME}`: User ka naam
- `{ID}`: User ki ID
- `{GROUPNAME}`: Group ka naam
"""

# --- FILTER SAVE KARNE KE LIYE ---
@app.on_message(filters.command("filter") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def save_filters(_, message):
    try:
        if len(message.command) < 2:
            return await message.reply_text(
                "**Sahi Tarika:**\nKisi message ko reply karein: `/filter [NAME]`"
            )

        replied_message = message.reply_to_message
        if not replied_message:
            return await message.reply_text("**Kripya kisi message, sticker ya video ko reply karein!**")

        # Get name from command
        name = message.text.split(None, 1)[1].strip().lower()

        if len(name) < 2:
            return await message.reply_text("**Filter name kam se kam 2 akshar ka hona chahiye.**")

        _type = "text"
        file_id = None
        data = None

        # Check for media types
        if replied_message.text:
            _type = "text"
            data = replied_message.text
        elif replied_message.sticker:
            _type = "sticker"
            file_id = replied_message.sticker.file_id
        elif replied_message.animation:
            _type = "animation"
            file_id = replied_message.animation.file_id
            data = replied_message.caption
        elif replied_message.photo:
            _type = "photo"
            file_id = replied_message.photo.file_id
            data = replied_message.caption
        elif replied_message.document:
            _type = "document"
            file_id = replied_message.document.file_id
            data = replied_message.caption
        elif replied_message.video:
            _type = "video"
            file_id = replied_message.video.file_id
            data = replied_message.caption
        elif replied_message.video_note:
            _type = "video_note"
            file_id = replied_message.video_note.file_id
        elif replied_message.audio:
            _type = "audio"
            file_id = replied_message.audio.file_id
            data = replied_message.caption
        elif replied_message.voice:
            _type = "voice"
            file_id = replied_message.voice.file_id
            data = replied_message.caption

        # Agar button wagera hain
        if data:
            data = await check_format(ikb, data)

        _filter = {
            "type": _type,
            "data": data,
            "file_id": file_id,
        }

        await save_filter(message.chat.id, name, _filter)
        return await message.reply_text(f"**Saved filter `{name}` in {message.chat.title}.**")

    except Exception as e:
        await message.reply_text(f"**Error:** `{e}`")


# --- FILTER TRIGGER (SIRF GROUPS MEIN) ---
@app.on_message((filters.text | filters.caption) & ~filters.private & ~filters.forwarded & ~BANNED_USERS, group=1)
async def filters_re(_, message: Message):
    text = message.text or message.caption
    if not text:
        return

    chat_id = message.chat.id
    list_of_filters = await get_filters_names(chat_id)
    if not list_of_filters:
        return

    for word in list_of_filters:
        pattern = r"( |^|[^\w])" + re.escape(word) + r"( |$|[^\w])"
        if re.search(pattern, text.lower(), flags=re.IGNORECASE):
            _filter = await get_filter(chat_id, word)
            if not _filter:
                continue

            data_type = _filter["type"]
            data = _filter["data"]
            file_id = _filter.get("file_id")
            keyb = None

            # Placeholders
            if data:
                if "{NAME}" in data: data = data.replace("{NAME}", message.from_user.mention if message.from_user else "User")
                if "{ID}" in data: data = data.replace("{ID}", str(message.from_user.id if message.from_user else "0"))
                if "{GROUPNAME}" in data: data = data.replace("{GROUPNAME}", message.chat.title)
                
                # Buttons handling
                if "[" in data and "]" in data:
                    keyboard = extract_text_and_keyb(ikb, data)
                    if keyboard:
                        data, keyb = keyboard

            # Reply logic for all media
            target = message.reply_to_message or message
            
            try:
                if data_type == "text":
                    await target.reply_text(data, reply_markup=keyb, disable_web_page_preview=True)
                elif data_type == "sticker":
                    await target.reply_sticker(file_id, reply_markup=keyb)
                elif data_type == "animation":
                    await target.reply_animation(file_id, caption=data, reply_markup=keyb)
                elif data_type == "photo":
                    await target.reply_photo(file_id, caption=data, reply_markup=keyb)
                elif data_type == "video":
                    await target.reply_video(file_id, caption=data, reply_markup=keyb)
                elif data_type == "document":
                    await target.reply_document(file_id, caption=data, reply_markup=keyb)
                elif data_type == "audio":
                    await target.reply_audio(file_id, caption=data, reply_markup=keyb)
                elif data_type == "voice":
                    await target.reply_voice(file_id, caption=data, reply_markup=keyb)
                elif data_type == "video_note":
                    await target.reply_video_note(file_id, reply_markup=keyb)
                else:
                    await target.reply_cached_media(file_id, caption=data, reply_markup=keyb)
            except Exception:
                pass
            return


# --- STOP FILTER ---
@app.on_message(filters.command("stop") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_filter_cmd(_, message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/stop [NAME]`")
    
    name = message.text.split(None, 1)[1].lower().strip()
    all_filters = await get_filters_names(message.chat.id)
    
    if name in all_filters:
        if delete_filter:
            await delete_filter(message.chat.id, name)
            await message.reply_text(f"**Stopped filter `{name}`.**")
        else:
            await message.reply_text("**Error:** Database delete function not found.")
    else:
        await message.reply_text("**Filter nahi mila.**")


# --- LIST FILTERS ---
@app.on_message(filters.command("filters") & ~filters.private & ~BANNED_USERS)
@capture_err
async def get_filterss(_, message):
    _filters = await get_filters_names(message.chat.id)
    if not _filters:
        return await message.reply_text("**Is group mein koi filters nahi hain.**")
    
    _filters.sort()
    msg = f"**{message.chat.title} ke filters:**\n"
    for _filter in _filters:
        msg += f"**-** `{_filter}`\n"
    await message.reply_text(msg)


# --- STOP ALL FILTERS ---
@app.on_message(filters.command("stopall") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_all(_, message):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Haan", callback_data="stop_yes"), InlineKeyboardButton("Nahi", callback_data="stop_no")]])
    await message.reply_text("**Kya aap sach mein saare filters delete karna chahte hain?**", reply_markup=keyboard)

@app.on_callback_query(filters.regex("stop_(.*)"))
async def stop_all_cb(_, cb):
    if cb.data == "stop_yes":
        await deleteall_filters(cb.message.chat.id)
        await cb.message.edit("**Saare filters delete kar diye gaye hain!**")
    else:
        await cb.message.delete()
