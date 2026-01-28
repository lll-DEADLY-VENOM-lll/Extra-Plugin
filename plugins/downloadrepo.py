import os
from pyrogram import filters
from pyrogram.types import Message
from github import Github
from github.GithubException import GithubException
from motor.motor_asyncio import AsyncIOMotorClient

# Import your app instance
from VIPMUSIC import app 

# --- CONFIGURATION ---
# Replace with your actual MongoDB URL
MONGO_DB_URL = "mongodb+srv://vishalpandeynkp:Bal6Y6FZeQeoAoqV@cluster0.dzgwt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
db = mongo_client["GitHubBot"]
tokens_col = db["user_tokens"]

# --- HELP TEXT ---
HELP_GUIDE = """
🧠 **GITHUB UPLOADER BOT - HELP MENU**
━━━━━━━━━━━━━━━━━━━━━━

🔐 **TOKEN SETUP**
๏ `/settoken <your_token>` : Save your GitHub Personal Access Token.
๏ `/deltoken` : Delete your token from the database.

📤 **UPLOADING**
๏ `/upload <repo_name>` : Reply to any file/zip to upload.
๏ `/upload <repo> <path/name.ext>` : Upload with a specific name or path.
๏ `/upload <repo> public` : Create a new public repo and upload.
๏ `/upload <repo> private` : Create a new private repo and upload.

🛠 **MANAGEMENT**
๏ `/rename_module <repo> <old_path> <new_path>` : Rename/Move files on GitHub.
๏ `/setwebhook <repo> <url>` : Setup a Push Webhook.
๏ `/delwebhook <repo>` : Remove all webhooks from a repo.

🚀 *This bot is public. Everyone must use their own GitHub token.*
━━━━━━━━━━━━━━━━━━━━━━
"""

# --- DATABASE FUNCTIONS ---
async def save_user_token(user_id, token):
    await tokens_col.update_one({"user_id": user_id}, {"$set": {"token": token}}, upsert=True)

async def get_user_token(user_id):
    result = await tokens_col.find_one({"user_id": user_id})
    return result["token"] if result else None

async def delete_user_token(user_id):
    await tokens_col.delete_one({"user_id": user_id})

# --- BASIC COMMANDS ---

@app.on_message(filters.command("start"))
async def start_handler(_, message: Message):
    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "I am a GitHub Uploader Bot. I can upload files directly to your repositories.\n\n"
        "**To get started:**\n"
        "1. Get your token from [GitHub Settings](https://github.com/settings/tokens)\n"
        "2. Use `/settoken <your_token>`\n"
        "3. Reply to any file with `/upload <repo_name>`",
        disable_web_page_preview=True
    )

@app.on_message(filters.command("help"))
async def help_handler(_, message: Message):
    await message.reply_text(HELP_GUIDE, disable_web_page_preview=True)

# --- TOKEN MANAGEMENT ---

@app.on_message(filters.command("settoken"))
async def set_token_handler(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `/settoken <github_token>`")
    
    token = message.command[1]
    await save_user_token(message.from_user.id, token)
    await message.reply_text("✅ **Success:** Your GitHub token has been saved securely!")

@app.on_message(filters.command("deltoken"))
async def del_token_handler(_, message: Message):
    await delete_user_token(message.from_user.id)
    await message.reply_text("🗑️ **Deleted:** Your token has been removed from the database.")

# --- CORE UPLOAD LOGIC ---

@app.on_message(filters.command("upload"))
async def upload_handler(_, message: Message):
    user_id = message.from_user.id
    token = await get_user_token(user_id)
    
    if not token:
        return await message.reply_text("🔑 **Access Denied:** Please set your token first using `/settoken`.")

    if not message.reply_to_message or not (message.reply_to_message.document or message.reply_to_message.audio or message.reply_to_message.video):
        return await message.reply_text("❌ **Error:** Please reply to a file or document with `/upload <repo_name>`")

    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `/upload <repository_name>`")

    repo_name = message.command[1]
    new_name_arg = message.command[2] if len(message.command) > 2 else None

    status_msg = await message.reply_text("⏳ **Processing...**")
    
    try:
        g = Github(token)
        user = g.get_user()
        
        # Repository Management
        try:
            repo = user.get_repo(repo_name)
        except Exception:
            is_private = True if new_name_arg == "private" else False
            repo = user.create_repo(repo_name, private=is_private)
            await status_msg.edit(f"🔨 **Created new {'private' if is_private else 'public'} repo:** `{repo_name}`")

        # Downloading file from Telegram
        await status_msg.edit("📥 **Downloading file to server...**")
        file_path = await message.reply_to_message.download()
        
        # Logic for filename/path
        filename = new_name_arg if (new_name_arg and "." in new_name_arg) else os.path.basename(file_path)

        with open(file_path, "rb") as f:
            content = f.read()

        # Upload or Update
        try:
            contents = repo.get_contents(filename)
            repo.update_file(contents.path, f"Update {filename} via Bot", content, contents.sha)
            await status_msg.edit(f"✅ **Updated:** `{filename}` in `{repo_name}`")
        except Exception:
            repo.create_file(filename, f"Upload {filename} via Bot", content)
            await status_msg.edit(f"🚀 **Uploaded:** `{filename}` to `{repo_name}`\n🔗 [View Repo]({repo.html_url})", disable_web_page_preview=True)

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await status_msg.edit(f"❌ **GitHub Error:** `{str(e)}`")

# --- ADVANCED REPO TOOLS ---

@app.on_message(filters.command("rename_module"))
async def rename_handler(_, message: Message):
    token = await get_user_token(message.from_user.id)
    if not token or len(message.command) < 4:
        return await message.reply_text("Usage: `/rename_module <repo> <old_path> <new_path>`")

    repo_name, old_path, new_path = message.command[1], message.command[2], message.command[3]
    try:
        g = Github(token)
        repo = g.get_user().get_repo(repo_name)
        file_content = repo.get_contents(old_path)
        repo.create_file(new_path, f"Rename {old_path} to {new_path}", file_content.decoded_content)
        repo.delete_file(file_content.path, f"Remove old {old_path}", file_content.sha)
        await message.reply_text(f"✅ **Renamed:** `{old_path}` ➜ `{new_path}`")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")

@app.on_message(filters.command("setwebhook"))
async def webhook_handler(_, message: Message):
    token = await get_user_token(message.from_user.id)
    if not token or len(message.command) < 3:
        return await message.reply_text("Usage: `/setwebhook <repo> <url>`")
    
    repo_name, webhook_url = message.command[1], message.command[2]
    try:
        g = Github(token)
        repo = g.get_user().get_repo(repo_name)
        config = {"url": webhook_url, "content_type": "json"}
        repo.create_hook("web", config, ["push"], active=True)
        await message.reply_text(f"✅ **Webhook set** for `{repo_name}`")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")

@app.on_message(filters.command("delwebhook"))
async def del_webhook_handler(_, message: Message):
    token = await get_user_token(message.from_user.id)
    if not token or len(message.command) < 2:
        return await message.reply_text("Usage: `/delwebhook <repo>`")
    
    repo_name = message.command[1]
    try:
        g = Github(token)
        repo = g.get_user().get_repo(repo_name)
        for hook in repo.get_hooks():
            hook.delete()
        await message.reply_text(f"✅ **All webhooks deleted** for `{repo_name}`")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")

# --- MODULE INFO FOR HELP MENU ---

__MODULE__ = "Rᴇᴘᴏ"
__HELP__ = HELP_GUIDE
