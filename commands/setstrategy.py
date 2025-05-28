from telegram import Update
from telegram.ext import CallbackContext

user_strategies = {}

def setstrategy(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        update.message.reply_text("Usage: /setstrategy <strategy_name>")
        return

    strategy = args[0].lower()

    # Optionally, validate against a list of supported strategies
    supported_strategies = ["momentum", "scalping", "meanreversion"]

    if strategy not in supported_strategies:
        update.message.reply_text(f"Unsupported strategy. Supported: {', '.join(supported_strategies)}")
        return

    user_strategies[user_id] = strategy
    update.message.reply_text(f"Strategy set to: {strategy}")
