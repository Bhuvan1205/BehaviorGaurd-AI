from datetime import datetime


def validate_event(event: dict):
    """
    Validate event-level inputs
    """

    if not event.get("user_id"):
        raise ValueError("user_id is required")

    if not event.get("timestamp"):
        raise ValueError("timestamp is required")

    try:
        datetime.fromisoformat(event["timestamp"])
    except:
        raise ValueError("Invalid timestamp format")

    if not event.get("device_id"):
        raise ValueError("device_id is required")


def validate_user_history(history: dict):
    """
    Validate user history inputs
    """

    if not history.get("past_logins"):
        raise ValueError("past_logins cannot be empty")

    if not history.get("logon_counts"):
        raise ValueError("logon_counts cannot be empty")

    if not history.get("unique_pcs_history"):
        raise ValueError("unique_pcs_history cannot be empty")

    # length consistency check
    if not (
        len(history["past_logins"]) ==
        len(history["logon_counts"]) ==
        len(history["unique_pcs_history"])
    ):
        raise ValueError("History arrays must have same length")

    # numeric sanity
    if history.get("current_logon_count", 0) < 0:
        raise ValueError("current_logon_count cannot be negative")

    if history.get("current_unique_pcs", 0) < 0:
        raise ValueError("current_unique_pcs cannot be negative")