from datetime import datetime


def _parse_timestamp(timestamp_str: str):
    """Parse ISO-like timestamps from the frontend, including milliseconds and Z suffixes."""
    if not timestamp_str:
        return None

    normalized = timestamp_str.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    for parser in (datetime.fromisoformat,):
        try:
            return parser(normalized)
        except ValueError:
            pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    return None


def _normalize_datetime(value: datetime | None):
    """Return a naive UTC-aligned datetime so arithmetic is consistent."""
    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)

    return value


def _cyclical_hour_distance(current_hour: float, baseline_hour: float) -> float:
    direct = abs(current_hour - baseline_hour)
    return min(direct, 24 - direct)

def compute_features(event: dict, user_history: dict) -> dict:
    """
    Compute the ordered 10-feature vector for a single real-time event.
    Returns a dictionary of features.
    """
    # SAFE MEAN / STD
    def safe_mean_std(values):
        if not values or len(values) < 2:
            return 0.0, 1.0
        mean = sum(values) / len(values)
        var = sum((x - mean) ** 2 for x in values) / len(values)
        std = var ** 0.5
        floor = max(1.0, abs(mean) * 0.35)
        return mean, std if std > floor else floor

    raw_logon_counts = user_history.get("logon_counts", [])
    raw_unique_pcs = user_history.get("unique_pcs_history", [])
    raw_logins = user_history.get("past_logins", [])

    avg_logon, std_logon = safe_mean_std(raw_logon_counts)
    avg_pcs, std_pcs = safe_mean_std(raw_unique_pcs)

    if avg_pcs == 0:
        avg_pcs = 1.0

    logon_count = user_history.get("current_logon_count", 1)
    logoff_count = user_history.get("current_logoff_count", 0)
    unique_pcs = user_history.get("current_unique_pcs", 1)

    timestamp_str = event.get("timestamp", "")
    current_dt = _normalize_datetime(_parse_timestamp(timestamp_str))
    hour = current_dt.hour if current_dt else 0

    mean_activity_hour = 12.0

    if raw_logins:
        hours = []
        parsed_history = []
        for t in raw_logins:
            try:
                parsed = _parse_timestamp(str(t))
                if parsed:
                    parsed = _normalize_datetime(parsed)
                    hours.append(parsed.hour)
                    parsed_history.append(parsed)
            except Exception:
                continue

        if hours:
            mean_activity_hour = sum(hours) / len(hours)
    else:
        parsed_history = []

    _std_logon = std_logon if std_logon > 0 else 1.0
    _std_pcs = std_pcs if std_pcs > 0 else 1.0

    upward_logon_delta = max(0.0, logon_count - avg_logon)
    upward_device_delta = max(0.0, unique_pcs - avg_pcs)

    z_logon = upward_logon_delta / _std_logon
    z_pcs = upward_device_delta / _std_pcs

    logon_deviation = upward_logon_delta
    device_deviation = upward_device_delta

    device_ratio = max(0.0, (unique_pcs / (avg_pcs + 1)) - 0.5)
    burst_score = max(0.0, (logon_count / (avg_logon + 1)) - 0.5)

    hour_deviation = max(0.0, _cyclical_hour_distance(hour, mean_activity_hour) - 2.0)

    session_gap = 0.0
    last_event_time = raw_logins[-1] if raw_logins else None
    historical_gaps = []

    if len(parsed_history) > 1:
        for index in range(1, len(parsed_history)):
            gap_hours = abs((parsed_history[index] - parsed_history[index - 1]).total_seconds()) / 3600.0
            historical_gaps.append(gap_hours)

    typical_gap = sum(historical_gaps) / len(historical_gaps) if historical_gaps else 4.0

    if last_event_time and current_dt:
        last_dt = _normalize_datetime(_parse_timestamp(str(last_event_time)))

        if last_dt:
            current_gap = abs((current_dt - last_dt).total_seconds()) / 3600.0
            session_gap = max(0.0, typical_gap - current_gap)

    logon_logoff_ratio = logon_count / (logoff_count + 1)

    night_activity_flag = bool(hour >= 22 or hour <= 6)

    features = {
        "z_logon": float(z_logon),
        "z_pcs": float(z_pcs),
        "logon_deviation": float(logon_deviation),
        "device_deviation": float(device_deviation),
        "device_ratio": float(device_ratio),
        "burst_score": float(burst_score),
        "hour_deviation": float(hour_deviation),
        "session_gap": float(session_gap),
        "logon_logoff_ratio": float(logon_logoff_ratio),
        "night_activity_flag": bool(night_activity_flag)
    }

    return features
