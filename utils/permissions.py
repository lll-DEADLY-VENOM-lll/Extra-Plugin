import logging
from functools import wraps
from traceback import format_exc as err

from pyrogram.errors.exceptions.forbidden_403 import ChatWriteForbidden
from pyrogram.types import Message

# Spy se app aur sudoers import ho rahe hain
from Spy import app
from Spy.misc import SUDOERS

async def member_permissions(chat_id: int, user_id: int):
    """User ya Bot ki permissions check karne ke liye helper function."""
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if not member.privileges:
            return []
        
        # Privileges object se saari 'can_' permissions nikalna
        perms = []
        p = member.privileges
        if p.can_post_messages: perms.append("can_post_messages")
        if p.can_edit_messages: perms.append("can_edit_messages")
        if p.can_delete_messages: perms.append("can_delete_messages")
        if p.can_restrict_members: perms.append("can_restrict_members")
        if p.can_promote_members: perms.append("can_promote_members")
        if p.can_change_info: perms.append("can_change_info")
        if p.can_invite_users: perms.append("can_invite_users")
        if p.can_pin_messages: perms.append("can_pin_messages")
        if p.can_manage_video_chats: perms.append("can_manage_video_chats")
        return perms
    except Exception:
        return []

async def authorised(func, subFunc2, client, message, *args, **kwargs):
    """Function ko execute karne wala wrapper."""
    try:
        await func(client, message, *args, **kwargs)
    except ChatWriteForbidden:
        await app.leave_chat(message.chat.id)
    except Exception as e:
        logging.exception(e)
        # Error handling optimized
        error_msg = getattr(e, "MESSAGE", str(e))
        try:
            await message.reply_text(f"**Error:** `{error_msg}`")
        except:
            pass
    return subFunc2

async def unauthorised(message: Message, permission, subFunc2, bot_lacking_permission=False):
    """Permission na hone par message bhejne wala logic."""
    if bot_lacking_permission:
        text = (
            "💡 **I ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ᴘᴇʀᴍɪssɪᴏɴs ᴛᴏ ᴅᴏ ᴛʜɪs!**\n"
            f"**Rᴇǫᴜɪʀᴇᴅ:** `{permission}`"
        )
    else:
        text = (
            "🚫 **Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.**\n"
            f"**Mɪssɪɴɢ:** `{permission}`"
        )
    try:
        await message.reply_text(text)
    except ChatWriteForbidden:
        await app.leave_chat(message.chat.id)
    return subFunc2

async def bot_permissions(chat_id: int):
    """Bot ki apni permissions check karna."""
    return await member_permissions(chat_id, app.id)

def adminsOnly(permission):
    """Main Decorator jo handlers par use hota hai."""
    def subFunc(func):
        @wraps(func)
        async def subFunc2(client, message: Message, *args, **kwargs):
            if not message.chat:
                return
            
            chatID = message.chat.id

            # 1. Sabse pehle check karein ki kya Bot ke paas permission hai?
            bot_perms = await bot_permissions(chatID)
            if permission not in bot_perms:
                return await unauthorised(
                    message, permission, subFunc2, bot_lacking_permission=True
                )

            # 2. Check karein ki message bhejne wala koun hai (User ya Chat?)
            if not message.from_user:
                # Anonymous Admin check (Agar admin group ke naam se post kare)
                if message.sender_chat and message.sender_chat.id == chatID:
                    return await authorised(func, subFunc2, client, message, *args, **kwargs)
                return await unauthorised(message, permission, subFunc2)

            # 3. User permissions aur Sudo check
            userID = message.from_user.id
            if userID in SUDOERS:
                return await authorised(func, subFunc2, client, message, *args, **kwargs)

            user_perms = await member_permissions(chatID, userID)
            if permission not in user_perms:
                return await unauthorised(message, permission, subFunc2)

            return await authorised(func, subFunc2, client, message, *args, **kwargs)

        return subFunc2
    return subFunc
