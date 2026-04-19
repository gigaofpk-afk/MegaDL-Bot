import os
import logging
from pyrogram import Client, filters
from mega import Mega

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - MegaDL-Bot - %(message)s"
)
log = logging.getLogger("MegaDL-Bot")

# ---------------------------------------------------------
# Environment Variables
# ---------------------------------------------------------
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MEGA_EMAIL = os.getenv("MEGA_EMAIL", "")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    log.error("Missing one or more required Telegram environment variables.")
    raise SystemExit

# ---------------------------------------------------------
# Pyrogram Client (SESSION FIXED FOR RAILWAY)
# ---------------------------------------------------------
app = Client(
    session_name="/tmp/bot",   # <--- FIXED: Railway-safe session path
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ---------------------------------------------------------
# Mega.nz Login / Bypass Mode
# ---------------------------------------------------------
def get_mega_client():
    mega = Mega()
    if MEGA_EMAIL and MEGA_PASSWORD:
        log.info("Logging into Mega.nz account...")
        return mega.login(MEGA_EMAIL, MEGA_PASSWORD)
    else:
        log.info("Using Mega.nz bypass mode (no login).")
        return mega

# ---------------------------------------------------------
# Start Command
# ---------------------------------------------------------
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        "Send me a Mega.nz link and I will download it and upload to Telegram."
    )

# ---------------------------------------------------------
# Mega.nz Link Handler
# ---------------------------------------------------------
@app.on_message(filters.regex(r"https?://mega\.nz"))
async def mega_handler(client, message):
    url = message.text.strip()
    await message.reply_text("Processing your Mega.nz link...")

    try:
        mega = get_mega_client()
        m = mega.find(url)

        if not m:
            await message.reply_text("Invalid or unsupported Mega.nz link.")
            return

        # Download to /tmp (Railway-safe)
        log.info(f"Downloading: {m['name']}")
        file_path = mega.download(m, dest_path="/tmp")

        await message.reply_text("Uploading to Telegram...")
        await message.reply_document(file_path)

        log.info("Upload complete.")

    except Exception as e:
        log.error(f"Mega download error: {e}")
        await message.reply_text(f"Error: {e}")

# ---------------------------------------------------------
# Run Bot
# ---------------------------------------------------------
if __name__ == "__main__":
    log.info("Starting MegaDL-Bot...")
    app.run()
