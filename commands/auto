from telegram import Update
from telegram.ext import CallbackContext

# This would ideally be a database or persistent store
user_autobot_status = {}

def autobot(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args

    if not args or args[0].lower() not in ['enable', 'disable']:
        update.message.reply_text("Usage: /autobot enable|disable")
        return

    action = args[0].lower()
    if action == 'enable':
        user_autobot_status[user_id] = True
        update.message.reply_text("Autobot enabled.")
    else:
        user_autobot_status[user_id] = False
        update.message.reply_text("Autobot disabled.")
