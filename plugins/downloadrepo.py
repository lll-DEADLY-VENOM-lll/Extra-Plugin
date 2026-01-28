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

# --- HELP GUIDE ---
HELP_TEXT = """
🧠 **GITHUB UPLOADER BOT — ROOT UPLOAD**
━━━━━━━━━━━━━━━━━━━━━━
🚀 **Status:** Public

🔐 **TOKEN SETTINGS**
๏ `/settoken <token>` : Save your GitHub Token.
๏ `/deltoken` : Delete your token.

📤 **UPLOADING**
๏ `/upload <repo>` : Upload files directly to the ROOT.
   *(Auto-skips the extra parent folder inside ZIP)*
━━━━━━━━━━━━━━━━━━━━━━
"""

async def get_token(user_id):
    res = await tokens_col.find_one({"user_id": user_id})
    return res["token"] if res else None

@app.on_message(filters.command("settoken"))
async def set_token_cmd(_, message: Message):
    if len(message.command) < 2: return
    await tokens_col.update_one({"user_id": message.from_user.id}, {"$set": {"token": message.command[1]}}, upsert=True)
    await message.reply_text("✅ Token saved!")

@app.on_message(filters.command("deltoken"))
async def del_token_cmd(_, message: Message):
    await tokens_col.delete_one({"user_id": message.from_user.id})
    await message.reply_text("🗑️ Token deleted.")

# --- CORE UPLOAD LOGIC (FIXED FOR ROOT) ---

@app.on_message(filters.command("upload"))
async def github_upload(_, message: Message):
    user_id = message.from_user.id
    token = await get_token(user_id)
    
    if not token:
        return await message.reply_text("🔑 Set token first using `/settoken`.")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ Reply to a .zip file.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Provide repo name: `/upload <repo>`")
    
    repo_name = message.command[1]
    status = await message.reply_text("⏳ **Processing Root Upload...**")
    
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

            # --- ROOT FIX LOGIC ---
            # Check if there is only one folder inside the extracted zip
            contents = os.listdir(extract_dir)
            upload_from = extract_dir
            if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
                upload_from = os.path.join(extract_dir, contents[0])
                print(f"Skipping parent folder: {contents[0]}")

            await status.edit("🚀 **Uploading files to ROOT (front page)...**")
            count = 0
            for root, _, files in os.walk(upload_from):
                for f in files:
                    local_p = os.path.join(root, f)
                    # We use relative path from 'upload_from' to put files in root
                    git_p = os.path.relpath(local_p, upload_from)
                    
                    with open(local_p, "rb") as df:
                        content = df.read()
                    try:
                        old = repo.get_contents(git_p)
                        repo.update_file(old.path, f"Update {git_p}", content, old.sha)
                    except:
                        repo.create_file(git_p, f"Upload {git_p}", content)
                    count += 1
            
            await status.edit(f"✅ **Root Upload Success!**\n📦 Total `{count}` files uploaded directly to GitHub front page.")
            shutil.rmtree(extract_dir)
        else:
            # Normal single file upload
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f: content = f.read()
            try:
                old = repo.get_contents(filename)
                repo.update_file(old.path, f"Update {filename}", content, old.sha)
            except:
                repo.create_file(filename, f"Upload {filename}", content)
            await status.edit(f"✅ Uploaded `{filename}` to root.")

        if os.path.exists(file_path): os.remove(file_path)

    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)}`")

@app.on_message(filters.command(["start", "help"]))
async def help_cmd(_, message: Message):
    await message.reply_text(HELP_TEXT)

__MODULE__ = "Rᴇᴘᴏ"
__HELP__ = HELP_TEXT
