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
        mega_client = mega.login()
except Exception as e:
    logger.error(f"Failed to initialize Mega client: {e}")
    sys.exit(1)


# ---------- Helpers ----------
def is_mega_link(text: str) -> bool:
    return "mega.nz" in text


async def download_single(node, dest: str) -> str:
    """Download a single Mega file."""
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, mega_client.download, node, dest)
    return file_path


async def download_folder(url: str, dest: str) -> list:
    """Download all files inside a Mega folder."""
    loop = asyncio.get_running_loop()

    try:
        folder = await loop.run_in_executor(None, mega_client.find, url)
    except Exception:
        folder = None

    if not folder:
        raise ValueError("Folder not found or Mega blocked access.")

    # Get folder file list
    try:
        files = await loop.run_in_executor(None, mega_client.get_files, folder)
    except Exception as e:
        raise ValueError(f"Failed to list folder files: {e}")

    downloaded_files = []

    for file_id, file_info in files.items():
        if file_info["t"] == 0:  # 0 = file, 1 = folder
            try:
                node = mega_client.find(file_info["h"])
                file_path = await download_single(node, dest)
                downloaded_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to download file: {e}")

    return downloaded_files


# ---------- Handlers ----------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, message: Message):
    mode = "LOGIN" if USE_LOGIN else "BYPASS (anonymous)"
    await message.reply_text(
        f"👋 **MegaDL-Bot Ready**\n\n"
        f"Send me a Mega.nz link.\n"
        f"- File link → I download it\n"
        f"- Folder link → I download **ALL files automatically**\n\n"
        f"Current mode: **{mode}**"
    )


@app.on_message(filters.private & filters.text)
async def mega_handler(_, message: Message):
    url = message.text.strip()

    if not is_mega_link(url):
        await message.reply_text("Please send a valid **Mega.nz** link.")
        return

    status = await message.reply_text("🔄 Processing Mega link...")

    try:
        # Detect if folder or file
        if "/folder/" in url:
            await status.edit_text("📁 Folder detected — downloading all files...")

            files = await download_folder(url, "/tmp")

            if not files:
                await status.edit_text("❌ No files found in folder.")
                return

            for file_path in files:
                file_name = os.path.basename(file_path)
                await message.reply_document(
                    document=file_path,
                    caption=f"📥 `{file_name}`"
                )

            await status.edit_text("✅ All files downloaded and uploaded.")

        else:
            await status.edit_text("📄 File detected — downloading...")

            node = mega_client.find(url)
            if not node:
                raise ValueError("File not found.")

            file_path = await download_single(node, "/tmp")
            file_name = os.path.basename(file_path)

            await message.reply_document(
                document=file_path,
                caption=f"📥 `{file_name}`"
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
