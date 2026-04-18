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

OWNER_ID = int(os.getenv("OWNER_ID", "0")) if os.getenv("OWNER_ID") else None

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing one or more required Telegram environment variables.")
    sys.exit(1)

# ---------- Pyrogram Client ----------
app = Client(
    "MegaDL-Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ---------- Mega.nz Client (Dual Mode) ----------
mega = Mega()

USE_LOGIN = bool(MEGA_EMAIL and MEGA_PASSWORD)

try:
    if USE_LOGIN:
        logger.info("🔐 Using Mega.nz LOGIN mode")
        mega_client = mega.login(MEGA_EMAIL, MEGA_PASSWORD)
    else:
        logger.info("⚡ Using Mega.nz BYPASS (anonymous) mode")
        mega_client = mega.login()  # anonymous session
except Exception as e:
    logger.error(f"Failed to initialize Mega client: {e}")
    sys.exit(1)


# ---------- Helpers ----------
def is_mega_link(text: str) -> bool:
    return "mega.nz" in text


async def download_from_mega(url: str, dest: str) -> str:
    """
    Download file from Mega.nz using:
    - Login mode (if credentials exist)
    - Anonymous mode (if no credentials)
    """
    loop = asyncio.get_running_loop()
    logger.info(f"Starting MEGA download: {url}")

    # Find file node
    try:
        node = await loop.run_in_executor(None, mega_client.find, url)
    except Exception as e:
        logger.error(f"Error while finding MEGA node: {e}")
        node = None

    if not node:
        raise ValueError(
            "File not found or Mega.nz blocked access for this link."
        )

    # Download
    try:
        file_path = await loop.run_in_executor(None, mega_client.download, node, dest)
        logger.info(f"MEGA download finished: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error during MEGA download: {e}")
        if not USE_LOGIN:
            raise ValueError(
                f"Anonymous mode failed: {e}. "
                "Try setting MEGA_EMAIL and MEGA_PASSWORD for full login mode."
            )
        raise e


# ---------- Handlers ----------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, message: Message):
    mode = "LOGIN" if USE_LOGIN else "BYPASS (anonymous)"
    text = (
        "👋 **MegaDL-Bot is online.**\n\n"
        "Send me a **Mega.nz link**, and I’ll download the file and upload it here.\n\n"
        f"Current MEGA mode: **{mode}**\n"
        "- To use anonymous mode, leave MEGA_EMAIL/MEGA_PASSWORD empty.\n"
        "- To use login mode, set MEGA_EMAIL/MEGA_PASSWORD in Railway."
    )
    await message.reply_text(text)


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
