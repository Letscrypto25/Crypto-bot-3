
def send_alert(message):
    print(f"ALERT: {message}")

def log_event(message):
    print(f"[LOG] {message}")

def format_trade_message(action, profit_or_loss):
    direction = "📈 PROFIT" if profit_or_loss > 0 else "📉 LOSS"
    return f"{direction} from {action.upper()} — {profit_or_loss:.2f} USDT"
