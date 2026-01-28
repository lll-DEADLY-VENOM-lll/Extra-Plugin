import os
import zipfile
import shutil
from pyrogram import filters
from pyrogram.types import Message
from github import Github
from github.GithubException import GithubException
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIG & APP IMPORTS ---
from config import OWNER_ID, MONGO_DB_URL
from VIPMUSIC import app 

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
db = mongo_client["GitHubBotV2"]
tokens_col = db["user_tokens"]
auth_col = db["authorized_users"]

# --- HELP GUIDE ---
HELP_TEXT = """
🧠 **ɢɪᴛʜᴜʙ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ — ʜᴇʟᴘ ɢᴜɪᴅᴇ**
━━━━━━━━━━━━━━━━━━━━━━

📘 **Usage (Upload/Update):**
๏ **Upload File/Zip:** `/upload <repo_name>`
   *(Reply to a .zip to extract it automatically)*
๏ **Rename Upload:** `/upload <repo> <new_name.ext>`
๏ **Create Repo:** `/upload <repo> public` (or private)
๏ **Module Rename:** `/rename_module <repo> <old_path> <new_path>`

🛠️ **Automation & Webhooks:**
๏ **Set Webhook:** `/setwebhook <repo> <url>`
๏ **Delete Webhook:** `/delwebhook <repo>`

🔐 **Access & Token Setup:**
๏ **Set Token:** `/settoken <your_github_token>`
๏ **Del Token:** `/deltoken`

👑 **Admin Only (Owner):**
๏ **Grant Access:** `/access` [Reply to user]
๏ **Revoke Access:** `/revoke` [Reply to user]
๏ **List Access:** `/listaccess`
━━━━━━━━━━━━━━━━━━━━━━
"""

# --- HELPERS (Authorization & Tokens) ---
async def is_authorized(user_id):
    # Check if user is the main owner from config.py
    if user_id == OWNER_ID:
        return True
    # Check if user is approved in database
    user = await auth_col.find_one({"user_id": user_id})
    return True if user else False

async def get_token(user_id):
    res = await tokens_col.find_one({"user_id": user_id})
    return res["token"] if res else None

# --- ACCESS CONTROL (Owner Only) ---

@app.on_message(filters.command("access") & filters.user(OWNER_ID))
async def grant_access(_, message: Message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        await auth_col.update_one({"user_id": user_id}, {"$set": {"auth": True}}, upsert=True)
        await message.reply_text(f"✅ **Access Granted** to `{user_id}`. Now they can use the bot.")
    else:
        await message.reply_text("❌ Please reply to a user's message to grant them access.")

@app.on_message(filters.command("revoke") & filters.user(OWNER_ID))
async def revoke_access(_, message: Message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        await auth_col.delete_one({"user_id": user_id})
        await message.reply_text(f"❌ **Access Revoked** for `{user_id}`.")
    else:
        await message.reply_text("❌ Please reply to a user to revoke their access.")

@app.on_message(filters.command("listaccess") & filters.user(OWNER_ID))
async def list_access(_, message: Message):
    users = auth_col.find()
    out = "📋 **Authorized Users List:**\n"
    async for u in users:
        out += f"• `{u['user_id']}`\n"
    await message.reply_text(out if "•" in out else "No users authorized except Owner.")

# --- TOKEN MANAGEMENT ---

@app.on_message(filters.command("settoken"))
async def set_token_cmd(_, message: Message):
    if not await is_authorized(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this bot.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/settoken <your_github_token>`")
    
    await tokens_col.update_one(
        {"user_id": message.from_user.id}, 
        {"$set": {"token": message.command[1]}}, 
        upsert=True
    )
    await message.reply_text("✅ Your GitHub Token has been saved securely!")

@app.on_message(filters.command("deltoken"))
async def del_token_cmd(_, message: Message):
    await tokens_col.delete_one({"user_id": message.from_user.id})
    await message.reply_text("🗑️ Your GitHub token has been removed from database.")

# --- CORE UPLOAD & ZIP EXTRACTION ---

@app.on_message(filters.command("upload"))
async def github_upload(_, message: Message):
    user_id = message.from_user.id
    
    # 1. Authorization Check
    if not await is_authorized(user_id):
        return await message.reply_text("❌ **Access Denied.** You need approval from the Owner.")
    
    # 2. Token Check
    token = await get_token(user_id)
    if not token:
        return await message.reply_text("🔑 You haven't set your token. Use `/settoken` first.")

    # 3. Message Validation
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ Reply to a file or **.zip** folder to upload.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Provide a repository name: `/upload <repo>`")
    
    repo_name = message.command[1]
    extra_arg = message.command[2] if len(message.command) > 2 else None

    status = await message.reply_text("⏳ **Analyzing request...**")
    
    try:
        g = Github(token)
        user = g.get_user()
        
        # Repository Logic
        try:
            repo = user.get_repo(repo_name)
        except:
            is_priv = True if extra_arg == "private" else False
            repo = user.create_repo(repo_name, private=is_priv)
            await status.edit(f"🔨 Created new {'private' if is_priv else 'public'} repo: `{repo_name}`")

        # Download from Telegram
        await status.edit("📥 **Downloading from Telegram...**")
        file_path = await message.reply_to_message.download()
        
        # --- ZIP EXTRACTION & UPLOAD ---
        if file_path.endswith(".zip") and extra_arg not in ["public", "private"]:
            extract_dir = f"temp_extract_{user_id}"
            if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            await status.edit("📦 **Extracting ZIP contents...**")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            await status.edit("🚀 **Uploading files to GitHub individually...**")
            count = 0
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    local_p = os.path.join(root, f)
                    git_p = os.path.relpath(local_p, extract_dir)
                    with open(local_p, "rb") as df:
                        content = df.read()
                    try:
                        # Update if exists
                        old = repo.get_contents(git_p)
                        repo.update_file(old.path, f"Update {git_p}", content, old.sha)
                    except:
                        # Create if new
                        repo.create_file(git_p, f"Upload {git_p}", content)
                    count += 1
            
            await status.edit(f"✅ **Success!**\n📦 Total `{count}` files extracted and uploaded to `{repo_name}`.")
            shutil.rmtree(extract_dir)
        
        # --- SINGLE FILE UPLOAD ---
        else:
            filename = extra_arg if (extra_arg and "." in extra_arg) else os.path.basename(file_path)
            await status.edit(f"🚀 Uploading `{filename}` to GitHub...")
            with open(file_path, "rb") as f:
                content = f.read()
            try:
                old = repo.get_contents(filename)
                repo.update_file(old.path, f"Update {filename}", content, old.sha)
            except:
                repo.create_file(filename, f"Upload {filename}", content)
            await status.edit(f"✅ **Uploaded:** `{filename}` in repo `{repo_name}`")

        if os.path.exists(file_path): os.remove(file_path)

    except Exception as e:
        await status.edit(f"❌ **GitHub Error:** `{str(e)}`")

# --- OTHER MANAGEMENT COMMANDS ---

@app.on_message(filters.command("rename_module"))
async def rename_mod_cmd(_, message: Message):
    if not await is_authorized(message.from_user.id): return
    if len(message.command) < 4: 
        return await message.reply_text("Usage: `/rename_module <repo> <old_path> <new_path>`")
    
    token = await get_token(message.from_user.id)
    repo_n, old_p, new_p = message.command[1], message.command[2], message.command[3]
    try:
        repo = Github(token).get_user().get_repo(repo_n)
        file = repo.get_contents(old_p)
        repo.create_file(new_p, f"Rename {old_p}", file.decoded_content)
        repo.delete_file(file.path, f"Delete old {old_p}", file.sha)
        await message.reply_text(f"✅ Renamed `{old_p}` to `{new_p}`")
    except Exception as e: await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("setwebhook"))
async def set_webhook_cmd(_, message: Message):
    if not await is_authorized(message.from_user.id): return
    token = await get_token(message.from_user.id)
    if len(message.command) < 3: return
    try:
        repo = Github(token).get_user().get_repo(message.command[1])
        repo.create_hook("web", {"url": message.command[2], "content_type": "json"}, ["push"], active=True)
        await message.reply_text("✅ Webhook created successfully!")
    except Exception as e: await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command(["start", "help"]))
async def help_cmd_handler(_, message: Message):
    if not await is_authorized(message.from_user.id):
        return await message.reply_text("👋 Hello! This is a private GitHub Uploader. Contact the Owner for access.")
    await message.reply_text(HELP_TEXT)

__MODULE__ = "Rᴇᴘᴏ"
__HELP__ = HELP_TEXT
