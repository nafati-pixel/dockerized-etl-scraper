from datetime import date, datetime, timezone

def get_utc_date() -> date:
    """Returns the current date in UTC to prevent server timezone bugs."""
    return datetime.now(timezone.utc).date()
