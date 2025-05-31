from telegram import Update
from telegram.ext import CallbackContext
from utils.firebase import migrate_keys
from firebase_admin import db

def autobot_config(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    # Ensure keys are migrated to the correct structure
    migrate_keys(user_id)

    if len(args) < 2:
        update.message.reply_text("Usage: /autobot_config <key> <value>")
        return

    key = args[0].lower()
    value = ' '.join(args[1:])

    try:
        # Save config to Firebase under the user's record
        config_ref = db.reference(f"/users/{user_id}/autobot_config")
        config_ref.update({key: value})

        update.message.reply_text(
            f"✅ Autobot config saved to cloud:\n`{key}` = `{value}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        update.message.reply_text("⚠️ Failed to update config. Please try again.")
        raise e
