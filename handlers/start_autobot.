from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db
from utils.exchange import get_balance, get_price  # Adjust path if needed

async def start_autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        user_ref = db.reference(f"users/{user_id}")
        user_data = user_ref.get()

        if not user_data:
            await update.message.reply_text("You are not registered. Use /register to begin.")
            return

        required_fields = ["exchange", "api_key", "secret", "strategy", "amount"]
        missing = [f for f in required_fields if f not in user_data]
        if missing:
            await update.message.reply_text(
                f"You're missing the following config: {', '.join(missing)}.\nUse /setplatform, /setstrategy, and /setamount to finish setup."
            )
            return

        # 💰 Check balance
        exchange = user_data["exchange"]
        balances = get_balance(user_id, exchange)

        # Determine user's balance in ZAR
        zar_value = 0
        if exchange == "luno":
            zar_value = balances.get("ZAR", 0)
        elif exchange == "binance":
            # Convert USDT or other stablecoin to ZAR
            usdt = balances.get("USDT", 0)
            usdt_price = get_price(user_id, source="luno", pair="USDTZAR") or 18  # fallback
            zar_value = usdt * usdt_price

        if zar_value < 100:
            await update.message.reply_text(
                "🧘‍♂️ Hey friend, looks like your balance is under R100.\n\nCome back when you’ve topped up a little — R100 is the minimum to let the bot do its thing. No stress. 🌱"
            )
            return

        if user_data.get("autobot"):
            await update.message.reply_text("🚀 Your auto-bot is already running.")
            return

        user_ref.update({"autobot": True})
        await update.message.reply_text(
            f"🤖 AutoBot started with R{zar_value:.2f} available.\n\nMinimum trade: R50\nUse /stopautobot anytime to chill."
        )

    except Exception as e:
        print(f"[Start AutoBot Error] {e}")
        await update.message.reply_text("Failed to start the bot. Please try again later.")
