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
🧠 **GITHUB UPLOADER BOT — 404 FIXED**
━━━━━━━━━━━━━━━━━━━━━━
🚀 **Auto-Create Repo feature is now active.**

🔐 **COMMANDS:**
๏ `/settoken <token>` : Save your Token.
๏ `/deltoken` : Delete your Token.
๏ **Generate Token:** [Click Here](https://github.com/settings/tokens)

📤 **UPLOADING:**
๏ `/upload <repo>` : Upload to ROOT. 
   *(If repo doesn't exist, I will create it!)*
━━━━━━━━━━━━━━━━━━━━━━
"""

async def get_token(user_id):
    if not MONGO_DB_URL: return None
    res = await tokens_col.find_one({"user_id": user_id})
    return res["token"] if res else None

@app.on_message(filters.command(["start", "help"]))
async def help_handler(_, message: Message):
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True)

@app.on_message(filters.command("settoken"))
async def set_token_cmd(_, message: Message):
    if len(message.command) < 2: return
    await tokens_col.update_one({"user_id": message.from_user.id}, {"$set": {"token": message.command[1]}}, upsert=True)
    await message.reply_text("✅ Token saved!")

@app.on_message(filters.command("deltoken"))
async def del_token_cmd(_, message: Message):
    await tokens_col.delete_one({"user_id": message.from_user.id})
    await message.reply_text("🗑️ Token removed.")

# --- CORE UPLOAD LOGIC (WITH AUTO-CREATE REPO FIX) ---

@app.on_message(filters.command("upload"))
async def github_upload(_, message: Message):
    user_id = message.from_user.id
    token = await get_token(user_id)
    
    if not token:
        return await message.reply_text("🔑 Set token first using `/settoken`.")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ Reply to a **.zip** file.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/upload <repo_name>`")
    
    repo_name = message.command[1]
    status = await message.reply_text("⏳ **Connecting to GitHub...**")
    
    try:
        g = Github(token)
        user = g.get_user()
        
        # --- FIXED: AUTO-CREATE REPO ON 404 ---
        try:
            repo = user.get_repo(repo_name)
        except Exception as e:
            if "404" in str(e):
                await status.edit(f"🔨 Repo `{repo_name}` not found. Creating it for you...")
                repo = user.create_repo(repo_name, auto_init=True)
                time.sleep(2) # Wait for GitHub to initialize
            else:
                raise e

        # Download file
        await status.edit("📥 **Downloading from Telegram...**")
        file_path = await message.reply_to_message.download()
        
        if file_path.endswith(".zip"):
            extract_dir = f"work_{user_id}"
            if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Skip parent folder logic
            contents = os.listdir(extract_dir)
            upload_from = extract_dir
            if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
                upload_from = os.path.join(extract_dir, contents[0])

            await status.edit("🚀 **Uploading files to GitHub Root...**")
            count = 0
            for root, _, files in os.walk(upload_from):
                for f in files:
                    local_p = os.path.join(root, f)
                    git_p = os.path.relpath(local_p, upload_from)
                    
                    with open(local_p, "rb") as df:
                        content = df.read()
                    
                    # Upload with SHA Conflict Fix (409)
                    try:
                        try:
                            old = repo.get_contents(git_p)
                            repo.update_file(old.path, f"Update {git_p}", content, old.sha)
                        except Exception as up_e:
                            if "404" in str(up_e):
                                repo.create_file(git_p, f"Upload {git_p}", content)
                            elif "409" in str(up_e):
                                # Re-fetch SHA on conflict
                                old = repo.get_contents(git_p)
                                repo.update_file(old.path, f"Fix: {git_p}", content, old.sha)
                            else:
                                raise up_e
                        count += 1
                    except Exception as fatal:
                        print(f"Failed {git_p}: {fatal}")
            
            await status.edit(f"✅ **Upload Success!**\n📦 Total `{count}` files added to `{repo_name}`.\n🔗 [View Repo]({repo.html_url})", disable_web_page_preview=True)
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
