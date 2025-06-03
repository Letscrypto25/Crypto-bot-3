from telegram import Update
from telegram.ext import ContextTypes  # Use ContextTypes instead of CallbackContext in v20+
from utils.firebase import migrate_keys
from firebase_admin import db

async def autobot_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    # Ensure keys are migrated to the correct structure
    migrate_keys(user_id)

    if len(args) < 2:
        await update.message.reply_text("Usage: /autobot_config <key> <value>")
        return

    key = args[0].lower()
    value = ' '.join(args[1:])

    try:
        # Save config to Firebase under the user's record
        config_ref = db.reference(f"/users/{user_id}/autobot_config")
        config_ref.update({key: value})

        await update.message.reply_text(
            f"✅ Autobot config saved to cloud:\n`{key}` = `{value}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to update config. Please try again.")
        raise e
