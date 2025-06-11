from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance  # Your synchronous function

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data by their Telegram ID
        user_data = firebase_ref.child(user_id).get()
        if not user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        # Determine exchange
        exchange = user_data.get("exchange", "").lower()
        if exchange not in ("luno", "binance"):
            await update.message.reply_text("❌ Unknown exchange specified in your data.")
            return

        # Get encrypted keys from DB, no decryption here
        api_key_encrypted = (
            user_data.get(f"{exchange}_api_key")
            or user_data.get("api_key")
        )
        secret_encrypted = (
            user_data.get(f"{exchange}_api_secret")
            or user_data.get("api_secret")
        )

        if not api_key_encrypted or not secret_encrypted:
            await update.message.reply_text(f"❌ Missing {exchange} API keys in your account.")
            return

        # Pass encrypted keys directly to get_balance()
        encrypted_user_data = {
            f"{exchange}_api_key": api_key_encrypted,
            f"{exchange}_api_secret": secret_encrypted,
        }

        # Run get_balance in executor to avoid blocking
        loop = asyncio.get_running_loop()
        balances = await loop.run_in_executor(
            None,
            get_balance,
            user_id,
            exchange,
            encrypted_user_data
        )

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format nicely
        balance_msg = f"💰 *Your {exchange.capitalize()} Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance  # Your synchronous function

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data by their Telegram ID
        user_data = firebase_ref.child(user_id).get()
        if not user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        # Determine exchange
        exchange = user_data.get("exchange", "").lower()
        if exchange not in ("luno", "binance"):
            await update.message.reply_text("❌ Unknown exchange specified in your data.")
            return

        # Get encrypted keys from DB, no decryption here
        api_key_encrypted = (
            user_data.get(f"{exchange}_api_key")
            or user_data.get("api_key")
        )
        secret_encrypted = (
            user_data.get(f"{exchange}_api_secret")
            or user_data.get("api_secret")
        )

        if not api_key_encrypted or not secret_encrypted:
            await update.message.reply_text(f"❌ Missing {exchange} API keys in your account.")
            return

        # Pass encrypted keys directly to get_balance()
        encrypted_user_data = {
            f"{exchange}_api_key": api_key_encrypted,
            f"{exchange}_api_secret": secret_encrypted,
        }

        # Run get_balance in executor to avoid blocking
        loop = asyncio.get_running_loop()
        balances = await loop.run_in_executor(
            None,
            get_balance,
            user_id,
            exchange,
            encrypted_user_data
        )

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format nicely
        balance_msg = f"💰 *Your {exchange.capitalize()} Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")
