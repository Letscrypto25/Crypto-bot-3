import datetime
from utils import send_alert

def evaluate_and_notify_user(user):
    notifications = user.get("notification_preferences", {})
    uid = user["user_id"]

    # Every trade notification
    if notifications.get("every_trade") and user.get("last_trade_result"):
        send_alert(f"[{uid}] Trade executed:\n{user['last_trade_result']}")

    # Profit threshold
    profit_threshold = notifications.get("profit_threshold")
    if profit_threshold is not None:
        profit = user.get("daily_profit", 0)
        if profit >= profit_threshold:
            send_alert(f"[{uid}] Congrats! You're up {profit * 100:.2f}% today.")

    # Loss threshold
    loss_threshold = notifications.get("loss_threshold")
    if loss_threshold is not None:
        loss = user.get("daily_profit", 0)
        if loss <= -abs(loss_threshold):
            send_alert(f"[{uid}] Heads up — you're down {loss * 100:.2f}% today.")

    # End-of-day summary (optional vibe check)
    if notifications.get("daily_summary") and _is_night_time():
        profit = user.get("daily_profit", 0)
        vibe = _get_vibe_message(profit)
        send_alert(f"[{uid}] Daily Report:\nProfit: {profit * 100:.2f}%\n{vibe}")

    # Suggestion if strategy underperforms
    if notifications.get("strategy_suggestion") and user.get("strategy_score", 1.0) < 0.5:
        send_alert(f"[{uid}] Your strategy is underperforming.\nConsider switching or taking a short break.")

    # Leaderboard update
    if notifications.get("leaderboard_updates") and _is_morning_time():
        rank = user.get("leaderboard_rank", None)
        if rank is not None:
            send_alert(f"[{uid}] Morning! You're currently ranked #{rank} on the leaderboard.")

# --- Helper functions ---

def _is_night_time():
    now = datetime.datetime.now()
    return now.hour == 21  # 9 PM

def _is_morning_time():
    now = datetime.datetime.now()
    return now.hour == 8  # 8 AM

def _get_vibe_message(profit):
    if profit > 0.05:
        return "You're killing it today — keep riding the wave!"
    elif profit > 0:
        return "You're doing good — solid gains."
    elif profit > -0.03:
        return "Small loss — no worries, tomorrow's a new day."
    else:
        return "It’s been rough — consider changing strategy or taking a breather."
