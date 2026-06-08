import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Feature column order (must match training) ────────────────────────────────
IF_FEATURES = [
    "z_logon", "z_pcs", "logon_deviation", "device_deviation",
    "device_ratio", "burst_score", "hour_deviation", "session_gap",
    "logon_logoff_ratio", "night_activity_flag",
]

def _safe_mean_std(values: list) -> tuple[float, float]:
    if len(values) < 2:
        return (float(values[0]) if values else 0.0), 1.0
    arr  = np.array(values, dtype=float)
    mean = float(arr.mean())
    std  = float(arr.std())
    floor = max(1.0, abs(mean) * 0.35)
    return mean, std if std > floor else floor


def _cyclical_hour_dist(h1: float, h2: float) -> float:
    direct = abs(h1 - h2)
    return min(direct, 24 - direct)


def _compute_features_for_window(
    row: pd.Series,
    user_history: dict,
) -> dict:
    """Compute the 10-feature vector for one user-hour window."""
    logon_hist  = user_history.get("logon_counts", [])
    pcs_hist    = user_history.get("unique_pcs_history", [])
    ts_hist     = user_history.get("past_timestamps", [])

    avg_logon, std_logon = _safe_mean_std(logon_hist)
    avg_pcs,   std_pcs   = _safe_mean_std(pcs_hist)
    if avg_pcs == 0:
        avg_pcs = 1.0

    logon_count  = int(row.get("logon_count",  1))
    logoff_count = int(row.get("logoff_count", 0))
    unique_pcs   = int(row.get("unique_pcs",   1))
    hour         = int(row["hour"])

    # Mean activity hour from history
    if ts_hist:
        hours_hist = [pd.Timestamp(t).hour for t in ts_hist if pd.notnull(t)]
        mean_activity_hour = float(np.mean(hours_hist)) if hours_hist else 12.0
    else:
        mean_activity_hour = 12.0

    _sl = std_logon if std_logon > 0 else 1.0
    _sp = std_pcs   if std_pcs   > 0 else 1.0

    up_logon  = max(0.0, logon_count  - avg_logon)
    up_device = max(0.0, unique_pcs   - avg_pcs)

    z_logon           = up_logon  / _sl
    z_pcs             = up_device / _sp
    logon_deviation   = up_logon
    device_deviation  = up_device
    device_ratio      = max(0.0, (unique_pcs / (avg_pcs + 1)) - 0.5)
    burst_score       = max(0.0, (logon_count / (avg_logon + 1)) - 0.5)
    hour_deviation    = max(0.0, _cyclical_hour_dist(hour, mean_activity_hour) - 2.0)

    # Session gap
    session_gap = 0.0
    if len(ts_hist) > 1:
        parsed = sorted(pd.to_datetime(ts_hist, errors="coerce").dropna())
        gaps   = [(parsed[i] - parsed[i-1]).total_seconds() / 3600
                  for i in range(1, len(parsed))]
        typical_gap = float(np.mean(gaps)) if gaps else 4.0
        last_ts = parsed[-1]
        cur_ts  = pd.Timestamp(row["window_start"])
        cur_gap = abs((cur_ts - last_ts).total_seconds()) / 3600.0
        session_gap = max(0.0, typical_gap - cur_gap)

    logon_logoff_ratio  = logon_count / (logoff_count + 1)
    night_activity_flag = bool(hour >= 22 or hour <= 6)

    return {
        "z_logon":            float(z_logon),
        "z_pcs":              float(z_pcs),
        "logon_deviation":    float(logon_deviation),
        "device_deviation":   float(device_deviation),
        "device_ratio":       float(device_ratio),
        "burst_score":        float(burst_score),
        "hour_deviation":     float(hour_deviation),
        "session_gap":        float(session_gap),
        "logon_logoff_ratio": float(logon_logoff_ratio),
        "night_activity_flag": night_activity_flag,
    }


def compute_features(df: pd.DataFrame, batch_date: str, cur) -> pd.DataFrame:
    """Group by user-hour, fetch baselines, and compute 10 behavioral features."""
    logger.info("Computing features for weekly batch...")
    
    # Build hourly windows
    df["hour"]         = df["timestamp"].dt.hour
    df["window_start"] = df["timestamp"].dt.floor("h")

    # Aggregate to user-hour level
    agg = (
        df.groupby(["user_id", "window_start", "hour"], as_index=False)
        .agg(
            logon_count  = ("logon_count",  "sum"),
            logoff_count = ("logoff_count", "sum"),
            unique_pcs   = ("unique_pcs",   "max"),
        )
    )
    agg["batch_date"] = batch_date

    # Fetch per-user history from DB (last 20 records per user)
    user_ids = agg["user_id"].unique().tolist()
    history_map: dict[str, dict] = {}

    if user_ids:
        placeholders = ",".join(["%s"] * len(user_ids))
        cur.execute(
            f"""
            SELECT DISTINCT ON (user_id, window_start)
                user_id, window_start,
                logon_count, unique_pcs
            FROM features.user_behavior_features
            WHERE user_id = ANY(ARRAY[{placeholders}]::uuid[])
            ORDER BY user_id, window_start DESC
            LIMIT 20
            """,
            user_ids,
        )
        rows = cur.fetchall()
        for row in rows:
            uid = str(row["user_id"])
            if uid not in history_map:
                history_map[uid] = {
                    "logon_counts":        [],
                    "unique_pcs_history":  [],
                    "past_timestamps":     [],
                }
            history_map[uid]["logon_counts"].append(int(row["logon_count"] or 1))
            history_map[uid]["unique_pcs_history"].append(int(row["unique_pcs"] or 1))
            history_map[uid]["past_timestamps"].append(str(row["window_start"]))

    # Compute features row-by-row
    feature_rows = []
    for _, row in agg.iterrows():
        uid   = str(row["user_id"])
        hist  = history_map.get(uid, {})
        feats = _compute_features_for_window(row, hist)
        feature_rows.append({**row.to_dict(), **feats})

    result = pd.DataFrame(feature_rows)
    logger.info("Computed %d hourly windows for %d users",
                len(result), result["user_id"].nunique())
    return result


def write_features_to_db(df: pd.DataFrame, batch_date: str, cur) -> None:
    """Save computed feature vectors into features.user_behavior_features."""
    logger.info("Writing %d rows to features.user_behavior_features ...", len(df))
    records = []
    for _, row in df.iterrows():
        records.append((
            str(row["user_id"]),
            batch_date,
            row["window_start"].isoformat() if hasattr(row["window_start"], "isoformat") else str(row["window_start"]),
            int(row.get("logon_count",  0) or 0),
            int(row.get("logoff_count", 0) or 0),
            int(row.get("unique_pcs",   1) or 1),
            int(row.get("hour",         0) or 0),
            float(row.get("z_logon",           0) or 0),
            float(row.get("z_pcs",             0) or 0),
            float(row.get("logon_deviation",   0) or 0),
            float(row.get("device_deviation",  0) or 0),
            float(row.get("device_ratio",      0) or 0),
            float(row.get("burst_score",       0) or 0),
            float(row.get("hour_deviation",    0) or 0),
            float(row.get("session_gap",       0) or 0),
            float(row.get("logon_logoff_ratio",0) or 0),
            bool(row.get("night_activity_flag", False)),
        ))

    cur.executemany(
        """
        INSERT INTO features.user_behavior_features
          (user_id, batch_date, window_start,
           logon_count, logoff_count, unique_pcs, hour,
           z_logon, z_pcs, logon_deviation, device_deviation,
           device_ratio, burst_score, hour_deviation, session_gap,
           logon_logoff_ratio, night_activity_flag)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        records,
    )
