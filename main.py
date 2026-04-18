import os
import sys
import asyncio
import logging

from dotenv import load_dotenv
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from mega import Mega

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("MegaDL-Bot")

# ---------- Env ----------
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MEGA_EMAIL = os.getenv("MEGA_EMAIL", "")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD", "")

if not all([API_ID, API_HASH, BOT_TOKEN, MEGA_EMAIL, MEGA_PASSWORD]):
    logger.error("Missing one or more required environment variables.")
    sys.exit(1)

# ---------- Pyrogram Client ----------
app = Client(
    "MegaDL-Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ---------- Mega.nz Client ----------
mega = Mega()
mega_client = mega.login(MEGA_EMAIL, MEGA_PASSWORD)


# ---------- Helpers ----------
async def download_from_mega(url: str, dest: str) -> str:
    """
    Download file from Mega.nz and return local path.
    """
    loop = asyncio.get_running_loop()
    logger.info(f"Starting MEGA download: {url}")
    node = await loop.run_in_executor(None, mega_client.find, url)
    if not node:
        raise ValueError("File not found on Mega.nz")

    file_path = await loop.run_in_executor(None, mega_client.download, node, dest)
    logger.info(f"MEGA download finished: {file_path}")
    return file_path


def is_mega_link(text: str) -> bool:
    return "mega.nz" in text


# ---------- Handlers ----------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, message: Message):
    await message.reply_text(
        "Send me a **Mega.nz link**, and I’ll download the file and upload it here."
    )


@app.on_message(filters.private & filters.text)
async def mega_handler(_, message: Message):
    text = message.text.strip()

    if not is_mega_link(text):
        await message.reply_text("Please send a valid **Mega.nz** link.")
        return

    status = await message.reply_text("🔄 Downloading from Mega.nz, please wait...")

    try:
        # Download to /tmp (Railway ephemeral FS)
        file_path = await download_from_mega(text, "/tmp")
        file_name = os.path.basename(file_path)

        await status.edit_text("⬆️ Uploading to Telegram...")
        await message.reply_document(
            document=file_path,
            caption=f"✅ Downloaded from Mega.nz\n`{file_name}`",
        )
        await status.delete()

    except Exception as e:
        logger.exception("Error in mega_handler")
        await status.edit_text(f"❌ Error: `{e}`")


# ---------- Startup ----------
async def start_app():
    try:
        await app.start()
        logger.info("🚀 MegaDL-Bot started successfully.")
        await idle()
    except Exception as e:
        logger.error(f"Startup error: {e}")
    finally:
        await app.stop()
        logger.info("🛑 MegaDL-Bot stopped.")


if __name__ == "__main__":
    asyncio.run(start_app())
