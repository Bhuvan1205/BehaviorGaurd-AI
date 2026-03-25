from datetime import datetime


def compute_features(event: dict, user_history: dict) -> list:
    """
    Compute the ordered 10-feature vector for a single real-time event.
    This version strictly preserves training feature semantics.
    """
    print("INPUT HISTORY:", user_history)
    print("CURRENT LOGON COUNT:", user_history.get("current_logon_count"))

    # -----------------------------
    # SAFE MEAN / STD
    # -----------------------------
    def safe_mean_std(values):
        if not values or len(values) < 2:
            return 0.0, 1.0
        mean = sum(values) / len(values)
        var = sum((x - mean) ** 2 for x in values) / len(values)
        std = var ** 0.5
        return mean, std if std > 0 else 1.0

    # -----------------------------
    # EXTRACT RAW HISTORY
    # -----------------------------
    raw_logon_counts = user_history.get("logon_counts", [])
    raw_unique_pcs = user_history.get("unique_pcs_history", [])
    raw_logins = user_history.get("past_logins", [])

    # -----------------------------
    # COMPUTE BASELINE STATS (MATCH TRAINING STYLE)
    # -----------------------------
    avg_logon, std_logon = safe_mean_std(raw_logon_counts)
    avg_pcs, std_pcs = safe_mean_std(raw_unique_pcs)

    if avg_pcs == 0:
        avg_pcs = 1.0

    # -----------------------------
    # CURRENT WINDOW VALUES
    # -----------------------------
    logon_count = user_history.get("current_logon_count", 1)
    logoff_count = user_history.get("current_logoff_count", 0)
    unique_pcs = user_history.get("current_unique_pcs", 1)

    # -----------------------------
    # TIMESTAMP PARSING
    # -----------------------------
    timestamp_str = event.get("timestamp", "")
    current_dt = None
    hour = 0

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            current_dt = datetime.strptime(timestamp_str, fmt)
            hour = current_dt.hour
            break
        except:
            continue

    # -----------------------------
    # MEAN ACTIVITY HOUR
    # -----------------------------
    mean_activity_hour = 12.0

    if raw_logins:
        hours = []
        for t in raw_logins:
            try:
                if "T" in t:
                    hours.append(int(t.split("T")[1].split(":")[0]))
                else:
                    hours.append(int(t.split(" ")[1].split(":")[0]))
            except:
                continue

        if hours:
            mean_activity_hour = sum(hours) / len(hours)

    # -----------------------------
    # STANDARDIZE STD (SAFE)
    # -----------------------------
    _std_logon = std_logon if std_logon > 0 else 1.0
    _std_pcs = std_pcs if std_pcs > 0 else 1.0

    # -----------------------------
    # FEATURE COMPUTATION (STRICT PARITY)
    # -----------------------------

    # 1. Z-SCORES
    z_logon = (logon_count - avg_logon) / _std_logon
    z_pcs = (unique_pcs - avg_pcs) / _std_pcs

    # 2. DEVIATIONS
    logon_deviation = logon_count - avg_logon
    device_deviation = unique_pcs - avg_pcs

    # 3. RATIOS
    device_ratio = unique_pcs / (avg_pcs + 1)
    burst_score = logon_count / (avg_logon + 1)

    # 4. TIME DEVIATION
    hour_deviation = abs(hour - mean_activity_hour)

    # 5. SESSION GAP
    session_gap = 0.0
    last_event_time = raw_logins[-1] if raw_logins else None

    if last_event_time and current_dt:
        last_dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                last_dt = datetime.strptime(last_event_time, fmt)
                break
            except:
                continue

        if last_dt:
            session_gap =abs((current_dt - last_dt).total_seconds()) / 3600.0

    # 6. LOGON / LOGOFF RATIO
    logon_logoff_ratio = logon_count / (logoff_count + 1)

    # 7. NIGHT FLAG
    night_activity_flag = 1 if (hour >= 22 or hour <= 6) else 0

    # -----------------------------
    # FINAL FEATURE VECTOR
    # -----------------------------
    features = [
        float(z_logon),
        float(z_pcs),
        float(logon_deviation),
        float(device_deviation),
        float(device_ratio),
        float(burst_score),
        float(hour_deviation),
        float(session_gap),
        float(logon_logoff_ratio),
        float(night_activity_flag),
    ]

    # -----------------------------
    # DEBUG (OPTIONAL)
    # -----------------------------
    import os
    if os.environ.get("DEBUG_FEATURES") == "1":
        print("RAW FEATURES:", features)

    return features
