import os
import shutil
from pyrogram import filters
from pyrogram.types import Message
from github import Github
from github.GithubException import GithubException

from VIPMUSIC import app

# --- CONFIG & STORAGE (Use MongoDB for production) ---
user_tokens = {}  # {user_id: "token"}
authorized_users = set()  # {user_id}
OWNER_ID = 12345678  # Replace with your actual Telegram User ID

# --- HELP GUIDE (Your exact text) ---
HELP_TEXT = """
🧠 ɢɪᴛʜᴜʙ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ — ʜᴇʟᴘ ɢᴜɪᴅᴇ
━━━━━━━━━━━━━━━━━━━━━━

📘 **Usage (Upload/Update):**
━━━━━━━━━━━━━━━━━━━━━━
๏ **Default Upload:**
   → `/upload <repo_name>`

๏ **Rename/Path Upload:**
   → `/upload <repo> <new_file/path.ext>`

๏ **Module/Folder Rename (Global):**
   → `/rename_module <repo> <old_path> <new_path>`

๏ **Create Repo + Upload:**
   → `/upload <repo> public` (or private)

๏ **Interactive Upload:**
   → `/upload`

━━━━━━━━━━━━━━━━━━━━━━
🛠️ **Automation & Webhooks**
━━━━━━━━━━━━━━━━━━━━━━
๏ **Set Webhook (Auto-Deployment):**
   → `/setwebhook <repo> <url>`
๏ **Delete Webhook:**
   → `/delwebhook <repo>`

🔐 **Access & Token Setup**
━━━━━━━━━━━━━━━━━━━━━━
๏ **Set Token:**
   → `/settoken <your_github_token>`
๏ **Grant Access to others:**
   → `/access [reply to user]`
๏ **Revoke Access:**
   → `/revoke [reply to user]`
๏ **List Access:**
   → `/listaccess`
๏ **Generate GitHub Token:**
   → [Click Here](https://github.com/settings/tokens)
━━━━━━━━━━━━━━━━━━━━━━
"""

# --- HELPERS ---
def is_auth(user_id):
    return user_id == OWNER_ID or user_id in authorized_users

# --- COMMANDS ---

@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    name = message.from_user.first_name
    await message.reply_text(f"""
👋 ʜᴇʟʟᴏ {name}!

🤖 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ɢɪᴛʜᴜʙ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ
━━━━━━━━━━━━━━━━━━━━━━
📤 ᴛʜɪs ʙᴏᴛ ʜᴇʟᴘs ʏᴏᴜ ᴜᴘʟᴏᴀᴅ:
• ғɪʟᴇs
• ғᴏʟᴅᴇʀs (.zip)
• ᴘʀᴏᴊᴇᴄᴛs
ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ʏᴏᴜʀ ɢɪᴛʜᴜʙ ʀᴇᴘᴏ 🚀
━━━━━━━━━━━━━━━━━━━━━━
{HELP_TEXT}
""", disable_web_page_preview=True)

@app.on_message(filters.command("help"))
async def help_cmd(_, message: Message):
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True)

# --- TOKEN & ACCESS ---

@app.on_message(filters.command("settoken"))
async def set_token(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/settoken your_github_token`")
    user_tokens[message.from_user.id] = message.command[1]
    await message.reply_text("✅ GitHub Token saved successfully!")

@app.on_message(filters.command("access") & filters.user(OWNER_ID))
async def grant_access(_, message: Message):
    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        user_id = int(message.command[1])
    
    if user_id:
        authorized_users.add(user_id)
        await message.reply_text(f"✅ Access granted to `{user_id}`")

@app.on_message(filters.command("listaccess") & filters.user(OWNER_ID))
async def list_access(_, message: Message):
    if not authorized_users:
        return await message.reply_text("No users authorized.")
    out = "Authorized Users:\n" + "\n".join([f"• `{u}`" for u in authorized_users])
    await message.reply_text(out)

# --- UPLOAD LOGIC ---

@app.on_message(filters.command("upload"))
async def github_upload(_, message: Message):
    user_id = message.from_user.id
    if not is_auth(user_id):
        return await message.reply_text("❌ You don't have access to use this bot.")
    
    if user_id not in user_tokens:
        return await message.reply_text("🔑 Please set your token first: `/settoken <token>`")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("Reply to a file/zip with `/upload <repo_name>`")

    # Parsing arguments
    args = message.command
    repo_name = args[1] if len(args) > 1 else None
    new_name = args[2] if len(args) > 2 else None # Could be 'public' or a filename

    if not repo_name:
        return await message.reply_text("Please provide a repository name.")

    msg = await message.reply_text("🚀 Starting upload process...")
    
    try:
        g = Github(user_tokens[user_id])
        user = g.get_user()
        
        # Repo Check/Creation
        try:
            repo = user.get_repo(repo_name)
        except:
            is_private = True if new_name == "private" else False
            repo = user.create_repo(repo_name, private=is_private)
            await msg.edit(f"🔨 Created new {'private' if is_private else 'public'} repo: {repo_name}")

        file_path = await message.reply_to_message.download()
        filename = new_name if (new_name and "." in new_name) else os.path.basename(file_path)

        with open(file_path, "rb") as f:
            content = f.read()

        try:
            contents = repo.get_contents(filename)
            repo.update_file(contents.path, f"Update {filename}", content, contents.sha)
            await msg.edit(f"✅ Updated `{filename}` in `{repo_name}`")
        except:
            repo.create_file(filename, f"Upload {filename}", content)
            await msg.edit(f"🚀 Uploaded `{filename}` to `{repo_name}`\n🔗 {repo.html_url}")

        os.remove(file_path)

    except Exception as e:
        await msg.edit(f"❌ Error: {str(e)}")

# --- REPO MANAGEMENT ---

@app.on_message(filters.command("rename_module"))
async def rename_module(_, message: Message):
    if not is_auth(message.from_user.id): return
    if len(message.command) < 4:
        return await message.reply_text("Usage: `/rename_module <repo> <old_path> <new_path>`")

    repo_name, old_p, new_p = message.command[1], message.command[2], message.command[3]
    try:
        g = Github(user_tokens[message.from_user.id])
        repo = g.get_user().get_repo(repo_name)
        file = repo.get_contents(old_p)
        repo.create_file(new_p, f"Rename {old_p} to {new_p}", file.decoded_content)
        repo.delete_file(file.path, f"Remove old {old_p}", file.sha)
        await message.reply_text(f"✅ Renamed `{old_p}` to `{new_p}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("setwebhook"))
async def set_webhook(_, message: Message):
    if not is_auth(message.from_user.id): return
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/setwebhook <repo> <url>`")
    
    repo_name, url = message.command[1], message.command[2]
    try:
        g = Github(user_tokens[message.from_user.id])
        repo = g.get_user().get_repo(repo_name)
        config = {"url": url, "content_type": "json"}
        repo.create_hook("web", config, ["push"], active=True)
        await message.reply_text(f"✅ Webhook set for `{repo_name}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

__MODULE__ = "Rᴇᴘᴏ"
__HELP__ = HELP_TEXT
