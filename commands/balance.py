from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data from Firebase
        user_data = firebase_ref.child(user_id).get()
        if not user_data or 'exchange' not in user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        exchange = user_data.get("exchange").lower()
        if not exchange:
            await update.message.reply_text("❌ No exchange specified.")
            return

        # Prepare API keys specifically for the exchange
        if exchange == "luno":
            luno_api_key_encrypted = user_data.get("luno_api_key")
            luno_api_secret_encrypted = user_data.get("luno_api_secret")
            if not luno_api_key_encrypted:
                await update.message.reply_text("❌ Missing luno_api_key.")
                return
            if not luno_api_secret_encrypted:
                await update.message.reply_text("❌ Missing luno_api_secret.")
                return

            luno_api_key = decrypt_data(luno_api_key_encrypted)
            luno_api_secret = decrypt_data(luno_api_secret_encrypted)

            if not luno_api_key or not luno_api_secret:
                await update.message.reply_text("❌ Luno API keys could not be decrypted.")
                return

            # Call get_balance with luno-specific keys
            balances = await get_balance(
                source="luno",
                luno_api_key=luno_api_key,
                luno_api_secret=luno_api_secret
            )

        elif exchange == "binance":
            binance_api_key_encrypted = user_data.get("binance_api_key")
            binance_api_secret_encrypted = user_data.get("binance_api_secret")
            if not binance_api_key_encrypted:
                await update.message.reply_text("❌ Missing binance_api_key.")
                return
            if not binance_api_secret_encrypted:
                await update.message.reply_text("❌ Missing binance_api_secret.")
                return

            binance_api_key = decrypt_data(binance_api_key_encrypted)
            binance_api_secret = decrypt_data(binance_api_secret_encrypted)

            if not binance_api_key or not binance_api_secret:
                await update.message.reply_text("❌ Binance API keys could not be decrypted.")
                return

            # Call get_balance with binance-specific keys
            balances = await get_balance(
                source="binance",
                binance_api_key=binance_api_key,
                binance_api_secret=binance_api_secret
            )

        else:
            await update.message.reply_text(f"❌ Unsupported exchange: {exchange}")
            return

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format balance nicely
        balance_msg = "💰 *Your Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")
