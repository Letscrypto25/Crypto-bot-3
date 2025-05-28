from telegram import Update
from telegram.ext import CallbackContext

# These should come from your actual config storage or user session storage
user_platforms = {}
user_strategies = {}
user_amounts = {}
user_bases = {}
user_autobot_status = {}

def showconfig(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    platform = user_platforms.get(user_id, "Not set")
    strategy = user_strategies.get(user_id, "Not set")
    amount = user_amounts.get(user_id, "Not set")
    base = user_bases.get(user_id, "Not set")
    autobot = user_autobot_status.get(user_id, False)

    autobot_status = "Enabled" if autobot else "Disabled"

    msg = (
        f"Your current configuration:\n"
        f"Platform: {platform}\n"
        f"Strategy: {strategy}\n"
        f"Trade Amount: {amount}\n"
        f"Base Currency: {base}\n"
        f"Autobot: {autobot_status}"
    )
    update.message.reply_text(msg)
