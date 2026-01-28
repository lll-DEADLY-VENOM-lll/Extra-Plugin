import os
import zipfile
import shutil
import time
from pyrogram import filters
from pyrogram.types import Message
from github import Github
from github.GithubException import GithubException
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIG & APP IMPORTS ---
try:
    try:
        from config import MONGO_DB_URI as MONGO_DB_URL
    except ImportError:
        from config import MONGO_DB_URL
except ImportError:
    MONGO_DB_URL = None 

from VIPMUSIC import app 

# --- DATABASE SETUP ---
if MONGO_DB_URL:
    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    db = mongo_client["GitHubPublicBot"]
    tokens_col = db["user_tokens"]

# --- BEAUTIFIED HELP GUIDE ---
HELP_TEXT = """
🧠 **GITHUB UPLOADER BOT — HELP GUIDE**
━━━━━━━━━━━━━━━━━━━━━━
🚀 **Status:** Public (Anyone can use)

🔐 **1. TOKEN SETTINGS**
๏ `/settoken <token>` : Save your GitHub Token.
๏ `/deltoken` : Delete your token from database.
๏ **Generate Token:** [Click Here to Create](https://github.com/settings/tokens)
   *(Note: Select 'repo' permissions while creating)*

📤 **2. UPLOADING FILES**
๏ `/upload <repo>` : Reply to a zip to upload to **ROOT**.
   *(Auto-skips the extra parent folder inside ZIP)*
๏ `/upload <repo> <new_name>` : Upload with custom name.

🛠️ **3. REPOSITORY TOOLS**
๏ `/rename_module <repo> <old_path> <new_path>` : Rename files.
๏ `/setwebhook <repo> <url>` : Create a push webhook.

━━━━━━━━━━━━━━━━━━━━━━
"""

# --- DATABASE HELPERS ---
async def get_token(user_id):
    if not MONGO_DB_URL: return None
    res = await tokens_col.find_one({"user_id": user_id})
    return res["token"] if res else None

# --- PUBLIC COMMANDS ---

@app.on_message(filters.command("start"))
async def start_handler(_, message: Message):
    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "I am a GitHub Uploader. I can extract .zip files and upload "
        "them directly to the **Root Directory** of your repo.\n\n"
        "**Steps to use:**\n"
        "1️⃣ Create a token: [Click Here](https://github.com/settings/tokens)\n"
        "2️⃣ Set it: `/settoken your_token`\n"
        "3️⃣ Reply to a zip: `/upload your_repo_name`\n\n"
        "Use /help for more info.",
        disable_web_page_preview=True
    )

@app.on_message(filters.command("help"))
async def help_handler(_, message: Message):
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True)

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
    await tokens_col.delete_one({"user_id": message.from_user.id})
    await message.reply_text("🗑️ **Deleted:** Your token has been removed.")

# --- CORE UPLOAD LOGIC (WITH SHA FIX & ROOT FIX) ---

@app.on_message(filters.command("upload"))
async def github_upload(_, message: Message):
    user_id = message.from_user.id
    token = await get_token(user_id)
    
    if not token:
        return await message.reply_text("🔑 **Access Denied:** Please set your token first using `/settoken`.")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ **Error:** Please reply to a **.zip** folder.")

    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:** `/upload <repo_name>`")
    
    repo_name = message.command[1]
    status = await message.reply_text("⏳ **Initializing Root Upload...**")
    
    try:
        g = Github(token)
        user = g.get_user()
        repo = user.get_repo(repo_name)

        file_path = await message.reply_to_message.download()
        
        if file_path.endswith(".zip"):
            extract_dir = f"work_{user_id}"
            if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Skip parent folder if ZIP contains only one folder
            contents = os.listdir(extract_dir)
            upload_from = extract_dir
            if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
                upload_from = os.path.join(extract_dir, contents[0])

            await status.edit("🚀 **Uploading files to Root (SHA Fix enabled)...**")
            count = 0
            for root, _, files in os.walk(upload_from):
                for f in files:
                    local_p = os.path.join(root, f)
                    git_p = os.path.relpath(local_p, upload_from)
                    
                    with open(local_p, "rb") as df:
                        content = df.read()
                    
                    # Upload with 409 Conflict Retry Logic
                    try:
                        try:
                            old = repo.get_contents(git_p)
                            repo.update_file(old.path, f"Update {git_p}", content, old.sha)
                        except Exception as e:
                            if "404" in str(e):
                                repo.create_file(git_p, f"Upload {git_p}", content)
                            elif "409" in str(e):
                                # Re-fetch SHA and retry
                                old = repo.get_contents(git_p)
                                repo.update_file(old.path, f"Fix: {git_p}", content, old.sha)
                            else:
                                raise e
                        count += 1
                    except Exception as upload_err:
                        print(f"Failed {git_p}: {upload_err}")
            
            await status.edit(f"✅ **Root Upload Success!**\n📦 Total `{count}` files uploaded to `{repo_name}` front page.")
            shutil.rmtree(extract_dir)
        
        else:
            # Single file logic
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f: content = f.read()
            try:
                try:
                    old = repo.get_contents(filename)
                    repo.update_file(old.path, f"Update {filename}", content, old.sha)
                except:
                    repo.create_file(filename, f"Upload {filename}", content)
                await status.edit(f"✅ Uploaded `{filename}`.")
            except: pass

        if os.path.exists(file_path): os.remove(file_path)

    except Exception as e:
        await status.edit(f"❌ **GitHub Error:** `{str(e)}`")

__MODULE__ = "Rᴇᴘᴏ"
__HELP__ = HELP_TEXT
