
from telegram.ext import Application, CommandHandler
from command import help_command, start_command  # import your handlers

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("help", help_command))

