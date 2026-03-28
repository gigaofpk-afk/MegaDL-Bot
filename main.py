import os
import sys
import asyncio
import logging
import socket
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, PeerIdInvalid, AuthKeyUnregistered
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Force IPv4 DNS resolution (Heroku fix)
socket.setdefaulttimeout(30)

class Config:
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))
    
    # Connection tweaks for Heroku
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "7"))
    RETRY_DELAY = int(os.environ.get("RETRY_DELAY", "8"))
    CONNECTION_TIMEOUT = int(os.environ.get("CONNECTION_TIMEOUT", "45"))

# Initialize client with Heroku-optimized settings
app = Client(
    "MegaDLBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=30,  # Reduce workers for free dynos
    ipv6=False,  # Force IPv4
    sleep_threshold=60,
    timeout=Config.CONNECTION_TIMEOUT,  # Increase timeout
    max_concurrent_transmissions=5,  # Limit concurrent requests
)

async def validate_credentials():
    """Check if API credentials are valid format"""
    if Config.API_ID <= 0 or len(Config.API_ID) < 5:
        logger.error("❌ Invalid API_ID - must be a positive integer from my.telegram.org")
        return False
    if len(Config.API_HASH) < 30:
        logger.error("❌ Invalid API_HASH - must be 32-character hex string")
        return False
    if not Config.BOT_TOKEN or ":" not in Config.BOT_TOKEN:
        logger.error("❌ Invalid BOT_TOKEN - format: 123456789:AAH...")
        return False
    logger.info("✅ Credentials format validated")
    return True

async def start_app():
    """Startup with robust connection handling"""
    
    # Step 1: Validate environment
    if not await validate_credentials():
        sys.exit(1)
    
    logger.info(f"🔄 Starting connection attempts (max: {Config.MAX_RETRIES})...")
    
    for attempt in range(1, Config.MAX_RETRIES + 1):
        try:
            logger.info(f"📡 Attempt {attempt}/{Config.MAX_RETRIES} - Connecting to Telegram...")
            
            # Pre-connection delay (helps Heroku network stabilize)
            if attempt > 1:
                delay = min(Config.RETRY_DELAY * attempt, 30)  # Cap at 30s
                logger.info(f"⏳ Waiting {delay}s before retry...")
                await asyncio.sleep(delay)
            
            # Attempt connection with explicit error handling
            await asyncio.wait_for(
                app.start(),
                timeout=Config.CONNECTION_TIMEOUT + 10  # Buffer time
            )
            
            # Verify connection worked
            me = await app.get_me()
            logger.info(f"✅ SUCCESS! Connected as @{me.username} (ID: {me.id})")
            
            # Send startup log
            if Config.LOG_CHANNEL:
                try:
                    await app.send_message(
                        Config.LOG_CHANNEL,
                        f"🟢 **Bot Online**\n`{datetime.now().isoformat()}`"
                    )
                except:
                    pass  # Don't crash if log channel fails
            
            logger.info("🎉 Bot is running! Waiting for messages...")
            await idle()
            break  # Exit loop on success
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Attempt {attempt}: Connection timed out after {Config.CONNECTION_TIMEOUT}s")
            
        except AuthKeyUnregistered:
            logger.error("❌ BOT_TOKEN is invalid or revoked! Check @BotFather")
            sys.exit(1)
            
        except PeerIdInvalid:
            logger.error("❌ API_ID/API_HASH mismatch or invalid!")
            sys.exit(1)
            
        except FloodWait as e:
            logger.warning(f"⚠️ Flood wait: {e.value}s")
            await asyncio.sleep(e.value)
            continue
            
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"❌ Attempt {attempt}: Network error - {type(e).__name__}: {e}")
            # Add diagnostic info
            try:
                socket.gethostbyname("api.telegram.org")
                logger.info("✓ DNS resolution works")
            except Exception as dns_err:
                logger.error(f"✗ DNS resolution failed: {dns_err}")
                
        except Exception as e:
            logger.error(f"❌ Attempt {attempt}: Unexpected error - {type(e).__name__}: {e}", exc_info=True)
        
        # If we reach max attempts, give up
        if attempt == Config.MAX_RETRIES:
            logger.critical("💥 All connection attempts failed!")
            logger.critical("🔧 Try these fixes:")
            logger.critical("   1. Verify API_ID/API_HASH from https://my.telegram.org")
            logger.critical("   2. Ensure BOT_TOKEN is correct and bot is active")
            logger.critical("   3. Add Aptfile + buildpacks for tgcrypto compilation")
            logger.critical("   4. Consider switching to Railway/Render (more reliable)")
            sys.exit(1)

async def idle():
    """Keep bot alive"""
    while True:
        await asyncio.sleep(1800)  # 30 minutes

# Basic command handlers
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(client, message: Message):
    await message.reply("👋 **MegaDL Bot is online!**\nSend a Mega.nz link to download.")

@app.on_message(filters.command("ping") & filters.private)
async def cmd_ping(client, message: Message):
    await message.reply("🏓 Pong! Bot is responsive.")

# Entry point
if __name__ == "__main__":
    logger.info("🚀 MegaDL Bot initializing...")
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
        asyncio.run(app.stop())
    except SystemExit:
        pass
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
