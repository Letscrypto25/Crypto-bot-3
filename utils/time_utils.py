# utils/time_utils.py

from datetime import datetime, timezone, timedelta

def get_utc_now() -> datetime:
    """Returns current UTC time."""
    return datetime.now(timezone.utc)

def get_local_time(offset_hours: int = 2) -> datetime:
    """Returns local time with a given UTC offset (default is UTC+2)."""
    return get_utc_now() + timedelta(hours=offset_hours)

def format_timestamp(ts: datetime) -> str:
    """Formats a datetime object to a readable string."""
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def time_since(ts: datetime) -> str:
    """Returns a human-readable duration since the given timestamp."""
    delta = get_utc_now() - ts
    total_minutes = int(delta.total_seconds() // 60)

    if total_minutes < 1:
        return "just now"
    elif total_minutes == 1:
        return "1 minute ago"
    elif total_minutes < 60:
        return f"{total_minutes} minutes ago"
    elif total_minutes < 1440:
        hours = total_minutes // 60
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = total_minutes // 1440
        return f"{days} day{'s' if days != 1 else ''} ago"
