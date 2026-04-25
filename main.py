#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import time
from contextlib import suppress

from pyrogram import Client, errors
from pyrogram.enums import ParseMode

# ─────────────────────────────────────────────────────────────
# Basic logging
# ─────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - [%(levelname)s] - MegaDL-Bot - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("MegaDL-Bot")

# ─────────────────────────────────────────────────────────────
# Environment / config
# ─────────────────────────────────────────────────────────────
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    log.error("API_ID / API_HASH / BOT_TOKEN missing in environment.")
    sys.exit(1)

SESSION_NAME = os.getenv("SESSION_NAME", "MegaDL-Bot")

# ─────────────────────────────────────────────────────────────
# Pyrogram client
# ─────────────────────────────────────────────────────────────
app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML,
)


# ─────────────────────────────────────────────────────────────
# Example handlers (keep your existing ones here)
# ─────────────────────────────────────────────────────────────
@app.on_message()
async def fallback_handler(client, message):
    # Keep or replace with your real handlers
    await message.reply_text("MegaDL-Bot is online and stable ✅")


# ─────────────────────────────────────────────────────────────
# Robust startup with retry + time-desync protection
# ─────────────────────────────────────────────────────────────
async def start_bot():
    """
    Start the bot with retries and explicit handling for BadMsgNotification[16].
    """
    # Small delay to let Railway sync NTP
    startup_delay = int(os.getenv("STARTUP_DELAY_SECONDS", "3"))
    if startup_delay > 0:
        log.info(f"Startup delay: sleeping {startup_delay}s before connecting...")
        await asyncio.sleep(startup_delay)

    max_retries = int(os.getenv("START_RETRIES", "10"))
    retry_delay = int(os.getenv("START_RETRY_DELAY_SECONDS", "5"))

    for attempt in range(1, max_retries + 1):
        try:
            log.info(f"Starting MegaDL-Bot... (attempt {attempt}/{max_retries})")
            await app.start()
            me = await app.get_me()
            log.info(
                f"MegaDL-Bot started as @{me.username} (id={me.id}). "
                f"Monotonic time: {os.getenv('PYROGRAM_USE_MONOTONIC_TIME', 'not set')}"
            )
            return
        except errors.BadMsgNotification as e:
            # This is the one you’re seeing: [16] msg_id too low / time desync
            log.error(
                f"BadMsgNotification while starting (code={getattr(e, 'code', None)}): "
                f"{e}. This usually means time desync. "
                f"Ensure PYROGRAM_USE_MONOTONIC_TIME=1 and session file is fresh."
            )
            if attempt == max_retries:
                log.critical("Max retries reached. Exiting.")
                raise
            log.info(f"Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            log.exception(f"Unexpected error while starting: {e}")
            if attempt == max_retries:
                log.critical("Max retries reached. Exiting.")
                raise
            log.info(f"Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)


async def idle_loop():
    """
    Simple idle loop to keep the bot running.
    """
    log.info("MegaDL-Bot is now running. Waiting for updates...")
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        log.info("Idle loop cancelled, shutting down...")


async def main():
    await start_bot()
    # If we reached here, app.start() succeeded
    idle_task = asyncio.create_task(idle_loop())

    try:
        await idle_task
    finally:
        with suppress(Exception):
            log.info("Stopping MegaDL-Bot...")
            await app.stop()
        log.info("MegaDL-Bot stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted by user, exiting...")
    except Exception as e:
        log.exception(f"Fatal error in main: {e}")
        sys.exit(1)
