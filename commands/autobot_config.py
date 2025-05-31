from telegram import Update
from telegram.ext import CallbackContext
from utils.firebase import migrate_keys
# Store user configs here — replace with database in real app
user_autobot_config = {}

def autobot_config(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args
    migrate_keys(user_id)
    
    if len(args) < 2:
        update.message.reply_text("Usage: /autobot_config <key> <value>")
        return

    key = args[0].lower()
    value = ' '.join(args[1:])

    if user_id not in user_autobot_config:
        user_autobot_config[user_id] = {}

    user_autobot_config[user_id][key] = value
    update.message.reply_text(f"Autobot config updated: {key} = {value}")
