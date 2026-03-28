import os
import sys
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, PeerIdInvalid
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
class Config:
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))
    UPDATES_CHANNEL = os.environ.get("UPDATES_CHANNEL", "")
    SESSION_STRING = os.environ.get("SESSION_STRING", "")
    
    # Retry configuration
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "5"))
    RETRY_DELAY = int(os.environ.get("RETRY_DELAY", "5"))

# Initialize the bot
app = Client(
    "MegaDLBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=50,
    ipv6=False,
    sleep_threshold=30
)

async def check_environment():
    """Verify all required environment variables are set"""
    required_vars = {
        "API_ID": Config.API_ID,
        "API_HASH": Config.API_HASH,
        "BOT_TOKEN": Config.BOT_TOKEN,
        "OWNER_ID": Config.OWNER_ID,
        "LOG_CHANNEL": Config.LOG_CHANNEL
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

async def test_connection():
    """Test if bot can connect to Telegram servers"""
    try:
        me = await app.get_me()
        logger.info(f"✅ Bot connected successfully as @{me.username}")
        return True
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False

async def send_startup_message():
    """Send startup notification to log channel"""
    try:
        if Config.LOG_CHANNEL:
            await app.send_message(
                Config.LOG_CHANNEL,
                f"🚀 **Bot Started Successfully!**\n\n"
                f"📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🤖 **Bot:** @{(await app.get_me()).username}\n"
                f"✅ **Status:** Online and Ready!"
            )
    except Exception as e:
        logger.warning(f"Could not send startup message: {e}")

async def start_app():
    """Main startup function with retry logic"""
    logger.info(" Checking environment variables...")
    if not await check_environment():
        logger.error("❌ Environment check failed. Exiting...")
        sys.exit(1)
    
    logger.info(f"🔄 Attempting to connect (max {Config.MAX_RETRIES} attempts)...")
    
    for attempt in range(1, Config.MAX_RETRIES + 1):
        try:
            logger.info(f"📡 Connection attempt {attempt}/{Config.MAX_RETRIES}")
            
            # Wait before attempting connection (helps with Heroku network initialization)
            if attempt > 1:
                delay = Config.RETRY_DELAY * (attempt - 1)  # Exponential backoff
                logger.info(f"⏳ Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)
            
            # Try to connect
            await app.start()
            
            # Test if connection is stable
            if await test_connection():
                logger.info("✅ Connection established and verified!")
                
                # Send startup message
                await send_startup_message()
                
                logger.info("\n" + "="*50)
                logger.info(" MEGADL BOT IS NOW ONLINE! 🎉")
                logger.info("="*50)
                logger.info(f"Bot Username: @{(await app.get_me()).username}")
                logger.info(f"Bot ID: {(await app.get_me()).id}")
                logger.info("="*50 + "\n")
                
                # Keep the bot running
                await idle()
                break  # Exit retry loop if successful
                
        except FloodWait as e:
            logger.warning(f"⚠️ Flood wait detected. Waiting {e.value} seconds...")
            await asyncio.sleep(e.value)
            continue
            
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"❌ Network error on attempt {attempt}: {type(e).__name__}: {e}")
            if attempt == Config.MAX_RETRIES:
                logger.error("❌ All connection attempts failed!")
                raise
                
        except PeerIdInvalid:
            logger.error("❌ Invalid BOT_TOKEN or API credentials!")
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"❌ Unexpected error on attempt {attempt}: {type(e).__name__}: {e}")
            if attempt == Config.MAX_RETRIES:
                raise
            continue
    
    else:
        logger.error("❌ Failed to connect after all attempts")
        sys.exit(1)

async def idle():
    """Keep the bot running"""
    logger.info("🔄 Bot is now idle and listening for messages...")
    while True:
        await asyncio.sleep(3600)  # Sleep for 1 hour

async def shutdown_handler(signum=None, frame=None):
    """Handle graceful shutdown"""
    logger.info("🛑 Shutting down bot gracefully...")
    try:
        await app.stop()
        logger.info("✅ Bot stopped successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    sys.exit(0)

# Bot command handlers
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Handle /start command"""
    try:
        await message.reply_text(
            f"👋 **Welcome to MegaDL Bot!**\n\n"
            f"📥 I can download files from Mega.nz\n"
            f"🎬 Support: Video, Audio, Documents\n"
            f"⚡ Fast and Reliable\n\n"
            f"Send me a Mega.nz link to get started!"
        )
        logger.info(f"📩 /start command from user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in start_command: {e}")

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    """Handle /help command"""
    try:
        await message.reply_text(
            f"📚 **Help Menu**\n\n"
            f" **How to use:**\n"
            f"1. Send me a Mega.nz link\n"
            f"2. I'll download and upload to Telegram\n\n"
            f"⚙️ **Commands:**\n"
            f"/start - Start the bot\n"
            f"/help - Show this help message\n"
            f"/status - Check download status\n"
            f"/cancel - Cancel current download\n\n"
            f"👨‍💻 **Support:** Contact @{(await client.get_me()).username}"
        )
    except Exception as e:
        logger.error(f"Error in help_command: {e}")

@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message: Message):
    """Handle /ping command"""
    try:
        start_time = datetime.now()
        msg = await message.reply_text(" Pinging...")
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds() * 1000
        
        await msg.edit_text(
            f"📊 **Pong!**\n\n"
            f"⚡ Latency: `{latency:.2f}ms`\n"
            f"✅ Bot is working perfectly!"
        )
    except Exception as e:
        logger.error(f"Error in ping_command: {e}")

# Error handler
@app.on_message(filters.private)
async def handle_messages(client, message: Message):
    """Handle all private messages"""
    try:
        # Check if message contains a Mega.nz link
        if message.text and "mega.nz" in message.text.lower():
            await message.reply_text(
                f"🔗 **Link received!**\n\n"
                f"📥 Starting download...\n"
                f"⏳ Please wait, this may take a while.\n\n"
                f"📌 Link: `{message.text}`"
            )
            # Add your Mega.nz download logic here
            logger.info(f"📥 Received Mega link from user {message.from_user.id}")
        else:
            await message.reply_text(
                f"❓ **I didn't understand that.**\n\n"
                f"Please send me a Mega.nz download link.\n"
                f"Use /help for more information."
            )
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")

# Main entry point
if __name__ == "__main__":
    logger.info("🚀 Starting MegaDL Bot...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Pyrogram version: {__import__('pyrogram').__version__}")
    
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        logger.info("👋 Received keyboard interrupt")
        asyncio.run(shutdown_handler())
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
