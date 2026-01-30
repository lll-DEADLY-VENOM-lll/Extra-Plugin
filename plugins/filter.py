import re
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import BANNED_USERS
from VIPMUSIC import app
from VIPMUSIC.utils.database import (
    deleteall_filters,
    get_filter,
    get_filters_names,
    save_filter,
    delete_filter # Make sure your DB utility has this function
)
from VIPMUSIC.utils.functions import (
    check_format,
    extract_text_and_keyb,
    get_data_and_name,
)
from VIPMUSIC.utils.keyboard import ikb
from VIPMUSIC.utils.error import capture_err
from VIPMUSIC.utils.permissions import adminsOnly, member_permissions
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
                "**ᴜsᴀɢᴇ:**\nʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴡɪᴛʜ  `/filter [FILTER_NAME]` ᴏʀ ᴜsᴇ `/filter [FILTER_NAME] [CONTENT]`"
            )

        replied_message = message.reply_to_message or message
        data, name = await get_data_and_name(replied_message, message)

        if len(name) < 2:
            return await message.reply_text("**Filter ka naam kam se kam 2 akshar ka hona chahiye.**")

        if data == "error":
            return await message.reply_text("**Kripya content dein ya kisi message ko reply karein.**")

        # Media Type check
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

        if replied_message.reply_markup and not re.findall(r"\[.+\,.+\]", data):
            urls = extract_urls(replied_message.reply_markup)
            if urls:
                response = "\n".join([f"{n}=[{t}, {u}]" for n, t, u in urls])
                data += response

        if data:
            data = await check_format(ikb, data)
            if not data:
                return await message.reply_text("**Format galat hai! Help section check karein.**")

        name = name.replace("_", " ").lower()
        _filter = {"type": _type, "data": data, "file_id": file_id}

        await save_filter(message.chat.id, name, _filter)
        return await message.reply_text(f"__**sᴀᴠᴇᴅ ғɪʟᴛᴇʀ `{name}`.**__")

    except Exception as e:
        return await message.reply_text(f"**Error:** `{e}`")

@app.on_message(filters.command("stop") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_filter(_, message):
    if len(message.command) < 2:
        return await message.reply_text("**ᴜsᴀɢᴇ:**\n`/stop [FILTER_NAME]`")
    
    name = message.text.split(None, 1)[1].lower().replace("_", " ")
    deleted = await delete_filter(message.chat.id, name)
    
    if deleted:
        await message.reply_text(f"**Stopped filter `{name}`.**")
    else:
        await message.reply_text("**Aisa koi filter nahi mila.**")

@app.on_message(filters.command("filters") & ~filters.private & ~BANNED_USERS)
@capture_err
async def get_filterss(_, message):
    _filters = await get_filters_names(message.chat.id)
    if not _filters:
        return await message.reply_text("**Chat mein koi filters nahi hain.**")
    
    _filters.sort()
    msg = f"**{message.chat.title}** ke filters ki list:\n"
    for _filter in _filters:
        msg += f"**-** `{_filter}`\n"
    await message.reply_text(msg)

@app.on_message(
    filters.text & ~filters.private & ~filters.channel & ~filters.via_bot & ~filters.forwarded & ~BANNED_USERS,
    group=1,
)
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
                # Placeholders Replacement
                if "{GROUPNAME}" in data: data = data.replace("{GROUPNAME}", message.chat.title)
                if "{NAME}" in data: data = data.replace("{NAME}", message.from_user.mention)
                if "{ID}" in data: data = data.replace("{ID}", str(message.from_user.id))
                if "{FIRSTNAME}" in data: data = data.replace("{FIRSTNAME}", message.from_user.first_name)
                if "{USERNAME}" in data: data = data.replace("{USERNAME}", f"@{message.from_user.username}" if message.from_user.username else "None")
                if "{DATE}" in data: data = data.replace("{DATE}", datetime.datetime.now().strftime("%Y-%m-%d"))
                if "{TIME}" in data: data = data.replace("{TIME}", datetime.datetime.now().strftime("%H:%M:%S"))

                if re.findall(r"\[.+\,.+\]", data):
                    keyboard = extract_text_and_keyb(ikb, data)
                    if keyboard: data, keyb = keyboard

            target_message = message.reply_to_message or message
            
            if data_type == "text":
                await target_message.reply_text(text=data, reply_markup=keyb, disable_web_page_preview=True)
            elif data_type == "sticker":
                await target_message.reply_sticker(sticker=file_id)
            elif data_type == "animation":
                await target_message.reply_animation(animation=file_id, caption=data, reply_markup=keyb)
            elif data_type == "photo":
                await target_message.reply_photo(photo=file_id, caption=data, reply_markup=keyb)
            elif data_type == "document":
                await target_message.reply_document(document=file_id, caption=data, reply_markup=keyb)
            elif data_type == "video":
                await target_message.reply_video(video=file_id, caption=data, reply_markup=keyb)
            elif data_type == "video_note":
                await target_message.reply_video_note(video_note=file_id)
            elif data_type == "audio":
                await target_message.reply_audio(audio=file_id, caption=data, reply_markup=keyb)
            elif data_type == "voice":
                await target_message.reply_voice(voice=file_id, caption=data, reply_markup=keyb)
            return

@app.on_message(filters.command("stopall") & ~filters.private & ~BANNED_USERS)
@adminsOnly("can_change_info")
async def stop_all(_, message):
    _filters = await get_filters_names(message.chat.id)
    if not _filters:
        await message.reply_text("**Is chat mein koi filters nahi hain.**")
    else:
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Yes, Delete All", callback_data="stop_yes"),
                InlineKeyboardButton("No, Cancel", callback_data="stop_no"),
            ]]
        )
        await message.reply_text(
            "**Kya aap sach mein saare filters delete karna chahte hain?**",
            reply_markup=keyboard,
        )

@app.on_callback_query(filters.regex("stop_(.*)") & ~BANNED_USERS)
async def stop_all_cb(_, cb):
    chat_id = cb.message.chat.id
    from_user = cb.from_user
    permissions = await member_permissions(chat_id, from_user.id)
    if "can_change_info" not in permissions:
        return await cb.answer("Aapke paas permission nahi hai.", show_alert=True)
    
    action = cb.data.split("_")[1]
    if action == "yes":
        await deleteall_filters(chat_id)
        await cb.message.edit("**Saare filters delete kar diye gaye hain.**")
    else:
        await cb.message.delete()
