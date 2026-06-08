#!/usr/bin/env python3
"""
BehaviorGuard-AI — Daily Log Generator
=======================================
Generates a realistic daily log CSV that mimics a full day of Windows
logon/logoff activity for all active users.

The CSV is consumed by the batch pipeline (run_batch_pipeline) — it does NOT
post to any API.

Usage
-----
    python tools/generate_daily_log.py [OPTIONS]

Options
-------
  --date      YYYY-MM-DD   Date to simulate         (default: today)
  --scenario  STR          normal | burst_alert |
                           night_intrusion |
                           device_spread             (default: normal)
  --output    PATH         Output CSV path           (default: data/daily_logs/<date>_log.csv)
  --seed      INT          Random seed               (default: 42)

Output columns
--------------
  user_id, timestamp, logon_count, logoff_count, unique_pcs,
  ip_address, source

  user_id is the alphanumeric employee_id (e.g. NFP2441), NOT the UUID.

Scenario behaviour (matches live_replay.py exactly)
----------------------------------------------------
  normal          — clean baseline traffic, 1–3 logons, 1 device per event
  burst_alert     — 35 % of events are credential-stuffing spikes
                    (10–20 logons, 8–15 devices, external IPs)
  night_intrusion — 35 % of events are off-hours (00:00–04:00)
                    with elevated logon/device counts
  device_spread   — 35 % of events show device proliferation
                    (3–6 logons, 5–8 devices)
"""

import argparse
import csv
import os
import random
import sys
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

# ── DB connection (mirrors app/api/db.py) ────────────────────────────────────

DB_CONFIG = dict(
    dbname   = "behavior_guard_ai",
    user     = "postgres",
    password = "Bhuvan2005!",
    host     = "localhost",
    port     = "5433",
)

# ── Scenario definitions (identical to live_replay.py / auto_replay.py) ──────

SCENARIOS = {
    "normal": {
        "anomaly_prob":  0.0,
    },
    "burst_alert": {
        "anomaly_prob":  0.35,
        "burst_logons":  (10, 20),
        "burst_devices": (8, 15),
        "external_ip":   True,
    },
    "night_intrusion": {
        "anomaly_prob":  0.35,
        "night_hours":   (0, 4),
        "burst_logons":  (5, 10),
        "burst_devices": (2, 4),
    },
    "device_spread": {
        "anomaly_prob":  0.35,
        "burst_logons":  (3, 6),
        "burst_devices": (5, 8),
    },
}

VALID_SCENARIOS = set(SCENARIOS)

# ── How many login events to generate per user per day ───────────────────────
# Typical enterprise user: 3–8 distinct logon windows across a shift
EVENTS_PER_USER_MIN = 3
EVENTS_PER_USER_MAX = 8


# ── IP helpers ────────────────────────────────────────────────────────────────

def _internal_ip() -> str:
    return f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"

def _external_ip() -> str:
    return f"185.{random.randint(10, 250)}.{random.randint(1, 254)}.{random.randint(1, 254)}"


# ── Per-user normal activity profile ─────────────────────────────────────────

def _normal_work_hour() -> int:
    """Pick a realistic business-hours timestamp (hour)."""
    # Weighted toward 08:00–17:00 with tapering edges
    weights = (
        [1] * 6      +   # 00-05  (very rare)
        [2] * 2      +   # 06-07  (early)
        [8] * 10     +   # 08-17  (core hours)
        [3] * 4      +   # 18-21  (late stay)
        [1] * 2          # 22-23  (very rare)
    )
    return random.choices(range(24), weights=weights, k=1)[0]


# ── Event factory ─────────────────────────────────────────────────────────────

def _make_event(employee_id: str, date: datetime.date, scenario: str) -> dict:
    """
    Build one logon-event row for a given user and scenario.
    Mirrors _make_payload() from auto_replay.py but outputs CSV columns.
    """
    cfg        = SCENARIOS[scenario]
    is_anomaly = random.random() < cfg.get("anomaly_prob", 0.0)

    # ── Timestamp ──────────────────────────────────────────────────────────
    if is_anomaly and scenario == "night_intrusion":
        lo, hi = cfg["night_hours"]
        hour   = random.randint(lo, hi)
    else:
        hour = _normal_work_hour()

    ts = datetime(
        date.year, date.month, date.day,
        hour,
        random.randint(0, 59),
        random.randint(0, 59),
    )

    # ── Counts & IP ────────────────────────────────────────────────────────
    if is_anomaly:
        lo, hi   = cfg.get("burst_logons",  (2, 5))
        dlo, dhi = cfg.get("burst_devices", (2, 4))
        logon_count  = random.randint(lo, hi)
        unique_pcs   = random.randint(dlo, dhi)
        ip_address   = _external_ip() if cfg.get("external_ip") else _internal_ip()
        source       = "log_anomaly"
    else:
        logon_count  = random.randint(1, 3)
        unique_pcs   = 1
        ip_address   = _internal_ip()
        source       = "daily_log"

    # Logoff count is always <= logon count (some sessions may not log off)
    logoff_count = random.randint(max(0, logon_count - 2), logon_count)

    return {
        "user_id":      employee_id,
        "timestamp":    ts.strftime("%Y-%m-%d %H:%M:%S"),
        "logon_count":  logon_count,
        "logoff_count": logoff_count,
        "unique_pcs":   unique_pcs,
        "ip_address":   ip_address,
        "source":       source,
    }


# ── DB helpers ────────────────────────────────────────────────────────────────

def _load_active_users() -> list[str]:
    """Fetch all active employee_ids from core.users."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT employee_id FROM core.users WHERE status = 'active' ORDER BY employee_id"
        )
        return [row["employee_id"] for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


# ── Generator ─────────────────────────────────────────────────────────────────

def generate_daily_log(
    date_str: str,
    scenario: str,
    output_path: str,
    seed: int,
) -> dict:
    """
    Generate a full day's log CSV and write it to output_path.

    Returns a summary dict with keys:
        date, scenario, output_path, total_users, total_events, anomaly_events
    """
    random.seed(seed)

    # Parse date
    try:
        sim_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"ERROR: --date must be YYYY-MM-DD, got: {date_str!r}", file=sys.stderr)
        sys.exit(1)

    if scenario not in VALID_SCENARIOS:
        print(
            f"ERROR: --scenario must be one of {sorted(VALID_SCENARIOS)}, got: {scenario!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load users
    print(f"Loading active users from DB ...")
    users = _load_active_users()
    if not users:
        print("ERROR: No active users found in core.users.", file=sys.stderr)
        sys.exit(1)
    print(f"  → {len(users)} active users loaded")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Generate events
    total_events   = 0
    anomaly_events = 0
    cfg            = SCENARIOS[scenario]

    print(f"Generating log for {date_str} | scenario={scenario} | seed={seed} ...")

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["user_id", "timestamp", "logon_count", "logoff_count",
                        "unique_pcs", "ip_address", "source"],
        )
        writer.writeheader()

        for employee_id in users:
            n_events = random.randint(EVENTS_PER_USER_MIN, EVENTS_PER_USER_MAX)
            for _ in range(n_events):
                row = _make_event(employee_id, sim_date, scenario)
                writer.writerow(row)
                total_events += 1
                if row["source"] == "log_anomaly":
                    anomaly_events += 1

    anomaly_pct = 100 * anomaly_events / max(total_events, 1)
    summary = {
        "date":           date_str,
        "scenario":       scenario,
        "output_path":    output_path,
        "total_users":    len(users),
        "total_events":   total_events,
        "anomaly_events": anomaly_events,
        "anomaly_pct":    round(anomaly_pct, 1),
    }

    print(f"\nDone.")
    print(f"  Output file   : {output_path}")
    print(f"  Total users   : {len(users)}")
    print(f"  Total events  : {total_events}")
    print(f"  Anomaly events: {anomaly_events} ({anomaly_pct:.1f}%)")

    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    today = datetime.utcnow().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(
        description="BehaviorGuard-AI — Daily Log Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--date",
        default=today,
        metavar="YYYY-MM-DD",
        help=f"Date to simulate (default: {today})",
    )
    parser.add_argument(
        "--scenario",
        default="normal",
        choices=sorted(VALID_SCENARIOS),
        help="Anomaly scenario to inject (default: normal)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Output CSV path (default: data/daily_logs/<date>_log.csv)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    output = args.output or os.path.join(
        "data", "daily_logs", f"{args.date}_log.csv"
    )

    generate_daily_log(
        date_str    = args.date,
        scenario    = args.scenario,
        output_path = output,
        seed        = args.seed,
    )


if __name__ == "__main__":
    main()
