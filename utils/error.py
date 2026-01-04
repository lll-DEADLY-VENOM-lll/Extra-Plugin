#
# Copyright (C) 2024 by Spy-Music Project
# Specialized for Spy Bot Structure
#

import traceback
from functools import wraps
from pyrogram.errors.exceptions.forbidden_403 import ChatWriteForbidden
from config import LOG_GROUP_ID
from Spy import app

def split_limits(text):
    """Telegram message limit (4096) ko handle karne ke liye text split karta hai."""
    if len(text) < 2048:
        return [text]

    lines = text.splitlines(True)
    small_msg = ""
    result = []
    for line in lines:
        if len(small_msg) + len(line) < 2048:
            small_msg += line
        else:
            result.append(small_msg)
            small_msg = line

    result.append(small_msg)
    return result


def capture_err(func):
    """
    Ek decorator jo handlers mein aane wale errors ko catch karta hai
    aur unhe Log Group mein bhejta hai.
    """
    @wraps(func)
    async def capture(client, message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except ChatWriteForbidden:
            # Agar bot ko message bhejne ki permission nahi hai, toh group chhod do
            try:
                await app.leave_chat(message.chat.id)
            except:
                pass
            return
        except Exception as err:
            # Pura error traceback format karein
            errors = traceback.format_exc()
            
            # User aur Chat ki info nikalein
            user_info = "Unknown User" if not message.from_user else f"{message.from_user.mention} (`{message.from_user.id}`)"
            chat_info = "Private" if not message.chat else (
                f"@{message.chat.username}" if message.chat.username else f"`{message.chat.id}`"
            )
            command_info = message.text or message.caption or "None"

            # Log message taiyar karein
            error_text = (
                f"**#ᴇʀʀᴏʀ_ʟᴏɢ**\n\n"
                f"**👤 ᴜsᴇʀ:** {user_info}\n"
                f"**👥 ᴄʜᴀᴛ:** {chat_info}\n"
                f"**💬 ᴄᴏᴍᴍᴀɴᴅ:** `{command_info}`\n\n"
                f"**📝 ᴛʀᴀᴄᴇʙᴀᴄᴋ:**\n```python\n{errors}```"
            )

            # Agar message bada hai toh split karke bhejein
            error_feedback = split_limits(error_text)
            for x in error_feedback:
                try:
                    await app.send_message(LOG_GROUP_ID, x)
                except:
                    print(f"Error logging failed: {errors}")
            
            # Error ko console par bhi dikhayein
            raise err

    return capture
