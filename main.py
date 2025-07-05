# === IMPORTS ===
import logging
import os
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === LOGGING SETUP ===
# A good logging setup is crucial for debugging a bot that runs 24/7.
# This will print informative messages to the console.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# We get the logger instance to use it in our functions.
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
# Load configuration from Replit Secrets (Environment Variables).
# This is more secure than hardcoding them in the script.
# It's also good practice to get the chat IDs from secrets.
try:
    TOKEN = os.environ['TOKEN']
    # Ensure the chat IDs are integers, as the API expects them to be.
    SOURCE_CHAT_ID = int(os.environ['GROUP_A_ID'])
    DESTINATION_CHAT_ID = int(os.environ['GROUP_B_ID'])
except (KeyError, ValueError) as e:
    logger.critical(f"CRITICAL ERROR: Missing or invalid environment variable: {e}. Please check your Replit Secrets.")
    # Exit if the configuration is missing, as the bot cannot run.
    exit()

# === KEEP-ALIVE SERVER (FOR REPLIT DEPLOYMENT) ===
# This Flask server is what Replit's Deployment feature will hook into.
# When deployed, Replit will continuously ping this server to keep it alive.
server = Flask('')

@server.route('/')
def home():
    # This page confirms to you and the Replit service that the bot is running.
    return "Telegram Forwarder Bot is alive and running!"

def run_flask_server():
    """Runs the Flask server in a separate thread to not block the bot."""
    # The server runs in a daemon thread. This means the thread will exit
    # when the main program (the bot) exits.
    thread = Thread(target=lambda: server.run(host='0.0.0.0', port=8080))
    thread.daemon = True
    thread.start()
    logger.info("Flask keep-alive server started in a background thread.")

# === TELEGRAM BOT LOGIC ===
async def forward_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles incoming messages, filters for the source chat,
    and forwards them to the destination chat.
    """
    # We use effective_chat to handle different update types correctly.
    # If the message is not from our source chat, we ignore it.
    if not update.effective_chat or update.effective_chat.id != SOURCE_CHAT_ID:
        return

    # The message object can be None for some updates, so we check for it.
    message = update.effective_message
    if not message:
        logger.warning("Received an update with no effective message, ignoring.")
        return

    try:
        # context.bot.copy_message is the best way to forward.
        # It works for text, photos, videos, stickers, etc., and looks clean.
        await context.bot.copy_message(
            chat_id=DESTINATION_CHAT_ID,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=message.message_id
        )
        logger.info(f"Successfully forwarded message_id: {message.message_id} from {SOURCE_CHAT_ID}.")
    except Exception as e:
        # If forwarding fails, we log the specific error and the message ID.
        logger.error(f"Failed to forward message_id: {message.message_id}. Error: {e}")

# === MAIN APPLICATION ===
if __name__ == '__main__':
    # 1. Start the Flask server in the background.
    run_flask_server()

    # 2. Create the bot application instance.
    application = Application.builder().token(TOKEN).build()

    # 3. Add the handler for forwarding messages.
    # We use filters.ALL to catch any type of message, but we explicitly
    # exclude commands so the bot doesn't forward its own commands.
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message_handler))

    # 4. Start the bot.
    # run_polling() is a blocking call that runs the bot until it's stopped.
    # The library handles the asyncio event loop internally.
    logger.info("Starting Telegram bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
