from telegram import Update
from telegram.ext import CallbackContext

user_bases = {}

def setbase(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        update.message.reply_text("Usage: /setbase <currency_code> (e.g. USD, BTC, ETH)")
        return

    base_currency = args[0].upper()
    # Optionally, you can validate against a list of supported currencies here

    user_bases[user_id] = base_currency
    update.message.reply_text(f"Base currency set to: {base_currency}")
