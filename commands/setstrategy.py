from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

# No longer using in-memory storage (user_strategies),
# because we'll use Firebase to persist the data.

async def setstrategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler for /setstrategy <strategy_name>
    Example: /setstrategy momentum

    This version stores the selected strategy in Firebase under:
    /users/{user_id}/strategy
    """

    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: /setstrategy <strategy_name>\n"
            "Example: /setstrategy momentum"
        )
        return

    strategy = args[0].lower()
    supported_strategies = ["momentum", "scalping", "meanreversion"]

    if strategy not in supported_strategies:
        await update.message.reply_text(
            f"❌ Unsupported strategy.\n"
            f"Supported strategies: {', '.join(supported_strategies)}"
        )
        return

    try:
        # Save to Firebase under the user's record
        db.reference(f"/users/{user_id}").update({
            "strategy": strategy
        })

        await update.message.reply_text(
            f"✅ Trading strategy saved to cloud:\n`{strategy}`",
            parse_mode="Markdown"
        )

    except Exception as e:
        # If there's an error (e.g. Firebase not set up),
        # let the user know and log the error for debugging.
        await update.message.reply_text(
            "⚠️ Failed to save your strategy. Please try again."
        )
        print(f"[setstrategy error] {e}")

# ⚠️ Note:
# 1️⃣ Ensure Firebase Admin SDK is initialized (usually at startup):
#    import firebase_admin
#    from firebase_admin import credentials
#    cred = credentials.Certificate("path/to/serviceAccountKey.json")
#    firebase_admin.initialize_app(cred, {'databaseURL': "https://<your-db>.firebaseio.com"})
#
# 2️⃣ This stores the strategy as:
#    /users/{telegram_user_id}/strategy
#
# 3️⃣ Later, you can retrieve this with:
#    user_data = db.reference(f"/users/{user_id}").get()
#    strategy = user_data.get("strategy")
