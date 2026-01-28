import os
import zipfile
import shutil
from pyrogram import filters
from pyrogram.types import Message
from github import Github
from github.GithubException import GithubException
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIG & APP IMPORTS ---
try:
    # Handling common naming differences for MongoDB URL in config.py
    try:
        from config import MONGO_DB_URI as MONGO_DB_URL
    except ImportError:
        from config import MONGO_DB_URL
except ImportError:
    MONGO_DB_URL = None 

from VIPMUSIC import app 

# --- DATABASE SETUP ---
if not MONGO_DB_URL:
    print("CRITICAL: MONGO_DB_URL not found in config.py!")
else:
    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    db = mongo_client["GitHubPublicBot"]
    tokens_col = db["user_tokens"]

# --- BEAUTIFIED HELP GUIDE ---
HELP_TEXT = """
🧠 **GITHUB UPLOADER BOT — HELP GUIDE**
━━━━━━━━━━━━━━━━━━━━━━
🚀 **Status:** Public (Anyone can use)

🔐 **1. TOKEN SETTINGS**
๏ `/settoken <token>` : Save your GitHub Personal Access Token.
๏ `/deltoken` : **REMOVE** your token from the bot's database.

📤 **2. UPLOADING FILES**
๏ `/upload <repo>` : Reply to a file or **.zip** archive.
   *(Note: .zip files are extracted automatically)*
๏ `/upload <repo> <new_name>` : Upload with a custom name.
๏ `/upload <repo> public` : Create a public repo and upload.
๏ `/upload <repo> private` : Create a private repo and upload.

🛠️ **3. REPOSITORY TOOLS**
๏ `/rename_module <repo> <old_path> <new_path>` : Rename GitHub files.
๏ `/setwebhook <repo> <url>` : Create a push webhook.
๏ `/delwebhook <repo>` : Delete all webhooks in a repo.

🔗 **Token Link:** [Generate Here](https://github.com/settings/tokens)
━━━━━━━━━━━━━━━━━━━━━━
"""

# --- DATABASE HELPERS ---
async def get_token(user_id):
    res = await tokens_col.find_one({"user_id": user_id})
    return res["token"] if res else None

# --- PUBLIC COMMANDS ---

@app.on_message(filters.command("start"))
async def start_handler(_, message: Message):
    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "I am a Public GitHub Uploader. I can extract .zip files and upload "
        "them directly to your GitHub repositories.\n\n"
        "**Usage:**\n"
        "1. Set your token: `/settoken <your_token>`\n"
        "2. Reply to a file/zip: `/upload <repo_name>`\n\n"
        "Use /help for more info."
    )

@app.on_message(filters.command("help"))
async def help_handler(_, message: Message):
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True)

# --- TOKEN MANAGEMENT (SET / DELETE) ---

@app.on_message(filters.command("settoken"))
async def set_token_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `/settoken <your_github_token>`")
    
    token = message.command[1]
    await tokens_col.update_one(
        {"user_id": message.from_user.id}, 
        {"$set": {"token": token}}, 
        upsert=True
    )
    await message.reply_text("✅ **Success:** Your GitHub Token has been saved!")

@app.on_message(filters.command("deltoken"))
async def del_token_cmd(_, message: Message):
    user_id = message.from_user.id
    check = await tokens_col.find_one({"user_id": user_id})
    if not check:
        return await message.reply_text("❌ You don't have any token saved to delete.")
    await tokens_col.delete_one({"user_id": user_id})
    await message.reply_text("🗑️ **Deleted:** Your GitHub token has been removed from the database.")

# --- CORE UPLOAD & ZIP EXTRACTION ---

@app.on_message(filters.command("upload"))
async def github_upload(_, message: Message):
    user_id = message.from_user.id
    token = await get_token(user_id)
    
    if not token:
        return await message.reply_text("🔑 **Access Denied:** Please set your token first using `/settoken`.")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ **Error:** Please reply to a file or **.zip** folder.")

    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `/upload <repo_name>`")
    
    repo_name = message.command[1]
    extra_arg = message.command[2] if len(message.command) > 2 else None

    status = await message.reply_text("⏳ **Initializing...**")
    
    try:
        g = Github(token)
        user = g.get_user()
        
        # Repository Handling
        try:
            repo = user.get_repo(repo_name)
        except:
            is_priv = True if extra_arg == "private" else False
            repo = user.create_repo(repo_name, private=is_priv)
            await status.edit(f"🔨 **Created new repo:** `{repo_name}`")

        # Download
        await status.edit("📥 **Downloading from Telegram...**")
        file_path = await message.reply_to_message.download()
        
        # --- ZIP EXTRACTION LOGIC ---
        if file_path.endswith(".zip") and extra_arg not in ["public", "private"]:
            extract_dir = f"work_{user_id}"
            if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            await status.edit("📦 **Extracting ZIP contents...**")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            await status.edit("🚀 **Uploading files individually to GitHub...**")
            count = 0
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    local_p = os.path.join(root, f)
                    git_p = os.path.relpath(local_p, extract_dir)
                    with open(local_p, "rb") as df:
                        content = df.read()
                    try:
                        # Update if exists, else create
                        old = repo.get_contents(git_p)
                        repo.update_file(old.path, f"Update {git_p}", content, old.sha)
                    except:
                        repo.create_file(git_p, f"Upload {git_p}", content)
                    count += 1
            
            await status.edit(f"✅ **Extraction Successful!**\n📦 Total `{count}` files uploaded to `{repo_name}`.")
            shutil.rmtree(extract_dir)
        
        # --- SINGLE FILE UPLOAD ---
        else:
            filename = extra_arg if (extra_arg and "." in extra_arg) else os.path.basename(file_path)
            await status.edit(f"🚀 **Uploading `{filename}`...**")
            with open(file_path, "rb") as f:
                content = f.read()
            try:
                old = repo.get_contents(filename)
                repo.update_file(old.path, f"Update {filename}", content, old.sha)
            except:
                repo.create_file(filename, f"Upload {filename}", content)
            await status.edit(f"✅ **Uploaded:** `{filename}` to `{repo_name}`\n🔗 [View Repo]({repo.html_url})", disable_web_page_preview=True)

        if os.path.exists(file_path): os.remove(file_path)

    except Exception as e:
        await status.edit(f"❌ **GitHub Error:** `{str(e)}`")

# --- OTHER TOOLS ---

@app.on_message(filters.command("rename_module"))
async def rename_mod_cmd(_, message: Message):
    token = await get_token(message.from_user.id)
    if not token or len(message.command) < 4: 
        return await message.reply_text("❌ **Usage:** `/rename_module <repo> <old_path> <new_path>`")
    
    repo_n, old_p, new_p = message.command[1], message.command[2], message.command[3]
    try:
        repo = Github(token).get_user().get_repo(repo_n)
        file = repo.get_contents(old_p)
        repo.create_file(new_p, f"Rename {old_p}", file.decoded_content)
        repo.delete_file(file.path, f"Delete old {old_p}", file.sha)
        await message.reply_text(f"✅ **Renamed:** `{old_p}` ➜ `{new_p}`")
    except Exception as e: await message.reply_text(f"❌ **Error:** {e}")

__MODULE__ = "Rᴇᴘᴏ"
__HELP__ = HELP_TEXT
