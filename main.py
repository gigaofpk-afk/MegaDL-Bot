# (c) Asm Safone
# A Part of MegaDL-Bot <https://github.com/AsmSafone/MegaDL-Bot>

import os
import time
import asyncio
from config import Config
from pyrogram import Client, idle

# Delay to allow Heroku clock to settle
time.sleep(3)

if __name__ == "__main__":
    if not os.path.isdir(Config.DOWNLOAD_LOCATION):
        os.makedirs(Config.DOWNLOAD_LOCATION)

    plugins = dict(root="megadl")

    app = Client(
        "MegaDL-Bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        plugins=plugins,
        ipv6=False,              # Force IPv4
        device_model="Heroku",   # Helps Pyrogram pick stable DC
        system_version="10",
        app_version="1.4"
    )

    async def start_app():
        await asyncio.sleep(1)
        await app.start()
        print('\n\n>>> MegaDL-Bot Started. Join @AsmSafone!')
        await idle()
        await app.stop()
        print('\n\n>>> MegaDL-Bot Stopped. Join @AsmSafone!')

    asyncio.get_event_loop().run_until_complete(start_app())
