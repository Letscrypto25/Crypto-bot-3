from telegram import Update
from telegram.ext import ContextTypes

# Temporary in-memory store for user's base currency choice
# In a real app, you’d store this in a database
user_bases = {}

async def setbase_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /setbase <currency_code>
    Example usage: /setbase USD
    """

    user_id = update.effective_user.id
    args = context.args  # Command arguments, e.g. [USD]

    # Check if the user provided any arguments
    if not args:
        # If no argument was provided, send usage instructions
        await update.message.reply_text("Usage: /setbase <currency_code> (e.g. USD, BTC, ETH)")
        return

    # Take the first argument and convert it to uppercase
    base_currency = args[0].upper()

    # Optional: validate the currency code against a known list
    # Example:
    # supported_currencies = {"USD", "BTC", "ETH"}
    # if base_currency not in supported_currencies:
    #     await update.message.reply_text("Unsupported currency code.")
    #     return

    # Save the user's base currency in our temporary store
    user_bases[user_id] = base_currency

    # Confirm to the user that the base currency was set
    await update.message.reply_text(
        f"✅ Base currency set to: `{base_currency}`",
        parse_mode="Markdown"
    )

# ⚠️ Note: 
# This example only stores the data in memory while the bot is running.
# For real use, save to a database like Firebase, MongoDB, or PostgreSQL
# so the data isn’t lost when the bot restarts.
