@app.on_message(filters.regex(r'https?://mega\.nz'))
async def mega_handler(client, message):
    url = message.text.strip()
    await message.reply_text("Processing your Mega.nz link...")

    try:
        mega = get_mega_client()

        # Detect file or folder
        if "/folder/" in url:
            log.info("Detected Mega folder link")
            m = mega.get_public_folder(url)
        else:
            log.info("Detected Mega file link")
            m = mega.get_public_url_info(url)

        if not m:
            await message.reply_text("Invalid or unsupported Mega.nz link.")
            return

        log.info(f"Downloading: {m['name']}")
        file_path = mega.download(m, dest_path="/tmp")

        await message.reply_text("Uploading to Telegram...")
        await message.reply_document(file_path)

        log.info("Upload complete.")

    except Exception as e:
        log.error(f"Mega download error: {e}")
        await message.reply_text(f"Error: {e}")
