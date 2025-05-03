import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define your command function(s)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello, I am your crypto trading bot!')

# Main function to set up the bot
async def main() -> None:
    """Start the bot."""
    # Initialize the application with your bot's token
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Add command handler (you can add more handlers as needed)
    application.add_handler(CommandHandler("start", start))

    # Set up webhook
    webhook_url = "https://your-fly-app-url.com/webhook/YOUR_BOT_TOKEN"
    
    # Set webhook
    await application.bot.set_webhook(webhook_url)
    
    # Start the webhook listener
    await application.run_webhook(
        listen="0.0.0.0",  # Listen on all interfaces
        port=8443,  # Port to listen on (make sure it's open in Fly.io)
        url_path="webhook/YOUR_BOT_TOKEN",  # Set the correct URL path for your webhook
        webhook_url=webhook_url,  # Provide the full URL for the webhook
        keyfile=None,  # Optionally add SSL keyfile if needed
        certfile=None,  # Optionally add SSL certificate if needed
    )

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
