from communities import AsyncIOScheduler # standard library for scheduling
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import enums, filters
from pyrogram.types import (
    CallbackQuery,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pyrogram.errors import ChatAdminRequired

# Yahan Spy se import ho raha hai
from Spy import app
from Spy.utils.nightmodedb import (
    get_nightchats,
    nightdb,
    nightmode_off,
    nightmode_on,
)

# --- Permissions Settings ---
CLOSE_CHAT = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_other_messages=False,
    can_send_polls=False,
    can_change_info=False,
    can_add_web_page_previews=False,
    can_pin_messages=False,
    can_invite_users=True,
)

OPEN_CHAT = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_other_messages=True,
    can_send_polls=True,
    can_change_info=True,
    can_add_web_page_previews=True,
    can_pin_messages=True,
    can_invite_users=True,
)

# --- Buttons ---
buttons = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("๏ ᴇɴᴀʙʟᴇ ๏", callback_data="add_night"),
            InlineKeyboardButton("๏ ᴅɪsᴀʙʟᴇ ๏", callback_data="rm_night"),
        ]
    ]
)

add_buttons = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text="๏ ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘ ๏",
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ]
    ]
)

# --- Handlers ---

@app.on_message(filters.command("nightmode") & filters.group)
async def _nightmode(_, message: Message):
    return await message.reply_photo(
        photo="https://telegra.ph//file/06649d4d0bbf4285238ee.jpg",
        caption="**ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ ᴏʀ ᴅɪsᴀʙʟᴇ ɴɪɢʜᴛᴍᴏᴅᴇ ɪɴ ᴛʜɪs ᴄʜᴀᴛ.**",
        reply_markup=buttons,
    )

@app.on_callback_query(filters.regex("^(add_night|rm_night)$"))
async def nightcb(_, query: CallbackQuery):
    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    
    # Fast Admin Check
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await query.answer("Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜsᴇ ᴛʜɪs!", show_alert=True)
    except Exception:
        return await query.answer("Error checking permissions.")

    check_night = await nightdb.find_one({"chat_id": chat_id})

    if data == "add_night":
        if check_night:
            await query.message.edit_caption("**๏ ɴɪɢʜᴛᴍᴏᴅᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ.**")
        else:
            await nightmode_on(chat_id)
            await query.message.edit_caption(
                "**๏ ɴɪɢʜᴛᴍᴏᴅᴇ ᴇɴᴀʙʟᴇᴅ!**\n\nGroup will auto-close at **12 AM** and open at **06 AM**."
            )

    elif data == "rm_night":
        if not check_night:
            await query.message.edit_caption("**๏ ɴɪɢʜᴛᴍᴏᴅᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ.**")
        else:
            await nightmode_off(chat_id)
            await query.message.edit_caption("**๏ ɴɪɢʜᴛᴍᴏᴅᴇ ᴅɪsᴀʙʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**")

# --- Scheduler Logic ---

async def start_nightmode():
    schats = await get_nightchats()
    for chat in schats:
        chat_id = int(chat["chat_id"])
        try:
            await app.set_chat_permissions(chat_id, CLOSE_CHAT)
            await app.send_photo(
                chat_id,
                photo="https://telegra.ph//file/06649d4d0bbf4285238ee.jpg",
                caption="**ɢʀᴏᴜᴘ ɪs ᴄʟᴏsɪɴɢ ɢᴏᴏᴅ ɴɪɢʜᴛ ᴇᴠᴇʀʏᴏɴᴇ!**\n\nMay you have long and blissful sleep full of happy dreams.",
                reply_markup=add_buttons
            )
        except Exception as e:
            print(f"Error in Nightmode start: {e}")

async def close_nightmode():
    schats = await get_nightchats()
    for chat in schats:
        chat_id = int(chat["chat_id"])
        try:
            await app.set_chat_permissions(chat_id, OPEN_CHAT)
            await app.send_photo(
                chat_id,
                photo="https://telegra.ph//file/14ec9c3ff42b59867040a.jpg",
                caption="**ɢʀᴏᴜᴘ ɪs ᴏᴘᴇɴɪɴɢ ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ ᴇᴠᴇʀʏᴏɴᴇ!**\n\nMay this day bring love and success to your heart.",
                reply_markup=add_buttons
            )
        except Exception as e:
            print(f"Error in Nightmode open: {e}")

# Single Scheduler Instance
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(start_nightmode, trigger="cron", hour=0, minute=0) # 12:00 AM IST
scheduler.add_job(close_nightmode, trigger="cron", hour=6, minute=0) # 06:00 AM IST
scheduler.start()

# --- Module Metadata ---
__MODULE__ = "Nɪɢʜᴛᴍᴏᴅᴇ"
__HELP__ = """
### /ɴɪɢʜᴛᴍᴏᴅᴇ
- **Usᴀɢᴇ:** Eɴᴀʙʟᴇ/Dɪsᴀʙʟᴇ ᴀᴜᴛᴏ ɢʀᴏᴜᴘ ᴄʟᴏsᴇ.
- **Tɪᴍᴇ:** Closes at 12 AM, Opens at 6 AM [IST].
- **Note:** Only for Admins.
"""
