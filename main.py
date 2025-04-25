import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from supabase import create_client, Client

# Supabase setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Start command
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username

    # Insert into Supabase
    response = supabase.table("users").insert({"telegram_id": user_id, "username": username}).execute()

    update.message.reply_text("Welcome to Let's Crypto! You've been added to the database.")

# Main bot runner
def main():
    token = os.environ.get("BOT_TOKEN")
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
