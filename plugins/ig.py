import re
import httpx
import asyncio
from pyrogram import filters
from VIPMUSIC import app
from config import LOG_GROUP_ID

# Instagram URL regex
INSTAGRAM_RE = re.compile(r"https?://(www\.)?instagram\.com/(reel|p|tv)/[a-zA-Z0-9_-]+/")

@app.on_message(filters.command(["ig", "instagram", "reel"]))
async def download_instagram_video(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ Iɴsᴛᴀɢʀᴀᴍ ʀᴇᴇʟ URL ᴀғᴛᴇʀ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ"
        )

    url = message.text.split()[1]
    
    if not INSTAGRAM_RE.match(url):
        return await message.reply_text(
            "Tʜᴇ ᴘʀᴏᴠɪᴅᴇᴅ URL ɪs ɴᴏᴛ ᴀ ᴠᴀʟɪᴅ Iɴsᴛᴀɢʀᴀᴍ URL😅😅"
        )

    m = await message.reply_text("ᴘʀᴏᴄᴇssɪɴɢ... ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ.")

    # Using a more stable public API
    # Note: If this API fails, you can replace it with another provider
    api_url = f"https://api.mantisapi.com/api/instagram?url={url}"

    try:
        async with httpx.AsyncClient(timeout=20) as session:
            response = await session.get(api_url)
            if response.status_code != 200:
                return await m.edit("Sᴇʀᴠᴇʀ Eʀʀᴏʀ! Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
            
            res = response.json()
            
            # API response check (Mantis API structure)
            if not res.get("status"):
                return await m.edit("Fᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ ᴠɪᴅᴇᴏ. Mᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ᴀᴄᴄᴏᴜɴᴛ ɪs ᴘᴜʙʟɪᴄ.")

            data = res.get("data", [])
            if not data:
                return await m.edit("Nᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ.")

            # Downloading first media item
            video_url = data[0].get("url")
            
            await m.delete()
            await message.reply_video(
                video=video_url,
                caption=f"✨ **Dᴏᴡɴʟᴏᴀᴅᴇᴅ ʙʏ:** @{app.username}"
            )

    except Exception as e:
        await m.edit(f"Eʀʀᴏʀ: `{str(e)}`")
        await app.send_message(LOG_GROUP_ID, f"IG Download Error: {e}")

__MODULE__ = "Rᴇᴇʟ"
__HELP__ = """
**ɪɴsᴛᴀɢʀᴀᴍ ʀᴇᴇʟ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ:**

• `/ig [URL]`: ᴅᴏᴡɴʟᴏᴀᴅ ɪɴsᴛᴀɢʀᴀᴍ ʀᴇᴇʟs.
• `/instagram [URL]`: ᴅᴏᴡɴʟᴏᴀᴅ ɪɴsᴛᴀɢʀᴀᴍ ʀᴇᴇʟs.
• `/reel [URL]`: ᴅᴏᴡɴʟᴏᴀᴅ ɪɴsᴛᴀɢʀᴀᴍ ʀᴇᴇʟs.
"""
