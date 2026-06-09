from __future__ import annotations

import json
import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.config import RISK_THRESHOLD
from app.core.model_loader import get_model, get_scaler, get_feature_list
import numpy as np
import pandas as pd


def _determine_shift(hour: int) -> str:
    if 9 <= hour <= 16:
        return "Day"
    if 17 <= hour <= 21:
        return "Evening"
    return "Night"


def _compute_seed_features(event_payload: dict, history_payload: dict) -> dict:
    """Lightweight inline feature computation for seeding, matching feature_engine logic."""
    logon_counts = history_payload.get("logon_counts", [])
    unique_pcs_history = history_payload.get("unique_pcs_history", [])
    past_logins = history_payload.get("past_logins", [])

    def safe_mean_std(values):
        if len(values) < 2:
            return (float(values[0]) if values else 0.0), 1.0
        arr = np.array(values, dtype=float)
        mean = float(arr.mean())
        std = float(arr.std())
        floor = max(1.0, abs(mean) * 0.35)
        return mean, std if std > floor else floor

    avg_logon, std_logon = safe_mean_std(logon_counts)
    avg_pcs, std_pcs = safe_mean_std(unique_pcs_history)
    if avg_pcs == 0:
        avg_pcs = 1.0

    logon_count = int(event_payload.get("logons", 1))
    logoff_count = int(history_payload.get("current_logoff_count", 0))
    unique_pcs = int(event_payload.get("devices", 1))

    ts = pd.Timestamp(event_payload["timestamp"])
    hour = ts.hour

    if past_logins:
        hours_hist = [pd.Timestamp(t).hour for t in past_logins if t]
        mean_activity_hour = float(np.mean(hours_hist)) if hours_hist else 12.0
    else:
        mean_activity_hour = 12.0

    _sl = std_logon if std_logon > 0 else 1.0
    _sp = std_pcs if std_pcs > 0 else 1.0

    up_logon = max(0.0, logon_count - avg_logon)
    up_device = max(0.0, unique_pcs - avg_pcs)

    z_logon = up_logon / _sl
    z_pcs = up_device / _sp
    logon_deviation = up_logon
    device_deviation = up_device
    device_ratio = max(0.0, (unique_pcs / (avg_pcs + 1)) - 0.5)
    burst_score = max(0.0, (logon_count / (avg_logon + 1)) - 0.5)

    direct = abs(hour - mean_activity_hour)
    hour_deviation = max(0.0, min(direct, 24 - direct) - 2.0)

    session_gap = 0.0
    if len(past_logins) > 1:
        parsed = sorted(pd.to_datetime(past_logins, errors="coerce").dropna())
        gaps = [(parsed[i] - parsed[i - 1]).total_seconds() / 3600 for i in range(1, len(parsed))]
        typical_gap = float(np.mean(gaps)) if gaps else 4.0
        last_ts = parsed[-1]
        cur_gap = abs((ts - last_ts).total_seconds()) / 3600.0
        session_gap = max(0.0, typical_gap - cur_gap)

    logon_logoff_ratio = logon_count / (logoff_count + 1)
    night_activity_flag = bool(hour >= 22 or hour <= 6)

    return {
        "z_logon": float(z_logon),
        "z_pcs": float(z_pcs),
        "logon_deviation": float(logon_deviation),
        "device_deviation": float(device_deviation),
        "device_ratio": float(device_ratio),
        "burst_score": float(burst_score),
        "hour_deviation": float(hour_deviation),
        "session_gap": float(session_gap),
        "logon_logoff_ratio": float(logon_logoff_ratio),
        "night_activity_flag": night_activity_flag,
    }

def predict(features: dict) -> tuple[int, float]:
    """Extremely fast mock predict for seeding to avoid CPU starvation / timeouts on Render.
    derive_demo_risk will still produce realistic risk scores.
    """
    logon_dev = float(features.get("logon_deviation", 0.0))
    device_dev = float(features.get("device_deviation", 0.0))
    hour_dev = float(features.get("hour_deviation", 0.0))
    
    deviation = logon_dev + device_dev * 2.0 + hour_dev
    if deviation > 4.0:
        score = -0.15 - (deviation - 4.0) * 0.02
        flag = 1
    else:
        score = 0.15 - deviation * 0.05
        flag = 0
    return flag, float(score)

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "behavior_guard_ai"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Bhuvan2005!"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433"),
}

SEED = 42
ORG_NAMESPACE = uuid.UUID("5f0f7fbe-64f9-4df4-b5ee-7bba2fd5ce99")
DEMO_START = date(2026, 3, 14)
DEMO_END = date(2026, 3, 27)

DEPARTMENTS = [
    "Security Operations",
    "Engineering",
    "Finance",
    "Human Resources",
    "Sales",
    "IT Support",
    "Legal",
    "Operations",
]

ROLES = [
    "Security Analyst",
    "Software Engineer",
    "Finance Manager",
    "HR Specialist",
    "Sales Executive",
    "IT Administrator",
    "Legal Counsel",
    "Operations Manager",
]

FIRST_NAMES = [
    "Aarav", "Ishaan", "Vivaan", "Ananya", "Diya", "Meera", "Rohan", "Kabir",
    "Arjun", "Neha", "Priya", "Saanvi", "Kavya", "Rahul", "Nikhil", "Aisha",
    "Fatima", "Zoya", "Aditya", "Reyansh", "Mira", "Tara", "Kiran", "Nisha",
    "Varun", "Sneha", "Pooja", "Ritika", "Dev", "Tanvi", "Riya", "Siddharth",
    "Parth", "Anika", "Ira", "Om", "Samar", "Yash", "Aditi", "Madhav",
]

LAST_NAMES = [
    "Mehta", "Sharma", "Patel", "Iyer", "Reddy", "Kapoor", "Nair", "Khanna",
    "Bose", "Malhotra", "Joshi", "Desai", "Gupta", "Bhat", "Chawla", "Pillai",
    "Sen", "Trivedi", "Saxena", "Menon",
]


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    employee_id: str
    full_name: str
    email: str
    department: str
    role: str
    status: str
    hire_date: date
    shift: str
    base_logons: int
    base_devices: int
    is_privileged: bool
    anomaly_pattern: str


def stable_uuid(label: str) -> str:
    return str(uuid.uuid5(ORG_NAMESPACE, label))


def ensure_monthly_partitions(cur) -> None:
    pass


def build_user_profiles() -> list[UserProfile]:
    random.seed(SEED)
    users: list[UserProfile] = []

    role_department_map = {
        "Security Analyst": "Security Operations",
        "Software Engineer": "Engineering",
        "Finance Manager": "Finance",
        "HR Specialist": "Human Resources",
        "Sales Executive": "Sales",
        "IT Administrator": "IT Support",
        "Legal Counsel": "Legal",
        "Operations Manager": "Operations",
    }

    shift_cycle = ["day", "day", "day", "day", "evening", "night"]
    anomaly_cycle = [
        "normal", "normal", "normal", "normal", "normal",
        "night_spike", "burst_login", "device_spread", "weekend_admin",
    ]

    total_users = 60
    for index in range(total_users):
        first = FIRST_NAMES[index % len(FIRST_NAMES)]
        last = LAST_NAMES[(index * 3) % len(LAST_NAMES)]
        full_name = f"{first} {last}"
        role = ROLES[index % len(ROLES)]
        department = role_department_map[role]
        shift = shift_cycle[index % len(shift_cycle)]
        anomaly_pattern = "burst_login" if index == 0 else anomaly_cycle[index % len(anomaly_cycle)]
        is_privileged = role in {"Security Analyst", "IT Administrator", "Finance Manager", "Legal Counsel"}
        hire_date = date(2021 + (index % 5), ((index % 12) + 1), ((index * 2) % 26) + 1)
        employee_id = f"DEMO-{1001 + index}"
        email_local = f"{first}.{last}.{1001 + index}".lower()
        user_id = stable_uuid(employee_id)

        base_logons = {
            "day": 2,
            "evening": 2,
            "night": 1,
        }[shift]
        base_devices = 1 if role not in {"IT Administrator", "Security Analyst"} else 2

        users.append(
            UserProfile(
                user_id=user_id,
                employee_id=employee_id,
                full_name=full_name,
                email=f"{email_local}@behaviorguard.demo",
                department=department,
                role=role,
                status="active",
                hire_date=hire_date,
                shift=shift,
                base_logons=base_logons,
                base_devices=base_devices,
                is_privileged=is_privileged,
                anomaly_pattern=anomaly_pattern,
            )
        )

    return users


def workdays_between(start_day: date, end_day: date) -> list[date]:
    days = []
    cursor = start_day
    while cursor <= end_day:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def shift_anchor_hour(shift: str) -> int:
    if shift == "day":
        return 9
    if shift == "evening":
        return 15
    return 23


def build_user_windows(profile: UserProfile, day_value: date) -> list[dict]:
    weekday = day_value.weekday()
    is_weekend = weekday >= 5
    rng = random.Random(f"{profile.employee_id}:{day_value.isoformat()}:{SEED}")
    windows: list[dict] = []

    if is_weekend and profile.role not in {"Security Analyst", "IT Administrator", "Operations Manager"}:
        if rng.random() < 0.88:
            return windows

    anchor = shift_anchor_hour(profile.shift)
    daily_windows = 1
    if profile.shift == "day":
        daily_windows = 2 if weekday < 5 else 1
    elif profile.shift == "evening":
        daily_windows = 2 if weekday < 5 and rng.random() < 0.65 else 1
    elif profile.shift == "night":
        daily_windows = 1 if rng.random() < 0.85 else 2

    for slot in range(daily_windows):
        minute = 5 + ((slot * 17 + weekday * 7) % 50)
        jitter = rng.randint(-1, 1)
        hour = max(0, min(23, anchor + slot + jitter))
        event_dt = datetime.combine(day_value, time(hour=hour, minute=minute))

        logons = profile.base_logons + (1 if slot == 0 and profile.shift == "day" else 0)
        devices = profile.base_devices

        if profile.role == "Sales Executive" and weekday < 5 and rng.random() < 0.35:
            devices = 2
        if profile.role == "Software Engineer" and slot == 1 and weekday < 5:
            logons += 1
        if profile.role == "IT Administrator" and weekday in {0, 2, 4}:
            logons += 1

        if profile.anomaly_pattern == "night_spike" and day_value >= date(2026, 3, 24) and weekday < 5:
            if slot == daily_windows - 1:
                event_dt = datetime.combine(day_value, time(hour=23, minute=40))
                logons += 6
                devices += 2
        elif profile.anomaly_pattern == "burst_login" and day_value >= date(2026, 3, 24):
            if slot == 0:
                logons += 10
        elif profile.anomaly_pattern == "device_spread" and day_value >= date(2026, 3, 26):
            devices += 4
            logons += 3
        elif profile.anomaly_pattern == "weekend_admin" and profile.is_privileged and is_weekend:
            event_dt = datetime.combine(day_value, time(hour=2, minute=15))
            logons += 4
            devices += 1

        windows.append(
            {
                "timestamp": event_dt.replace(microsecond=0),
                "logons": max(1, logons),
                "devices": max(1, devices),
            }
        )

    return sorted(windows, key=lambda item: item["timestamp"])


def classify_alert_status(event_time: datetime) -> str:
    if event_time.date() >= date(2026, 3, 26):
        return "OPEN"
    return "CLOSED"


def derive_demo_risk(profile: UserProfile, window: dict, features: dict, anomaly_score: float) -> tuple[bool, float]:
    logon_pressure = min(max(features["logon_deviation"], 0.0), 12.0) / 12.0
    device_pressure = min(max(features["device_deviation"], 0.0), 5.0) / 5.0
    hour_pressure = min(features["hour_deviation"], 10.0) / 10.0
    session_pressure = min(features["session_gap"], 16.0) / 16.0
    model_pressure = min(max(-anomaly_score, 0.0), 0.25) / 0.25

    risk = 0.08
    risk += 0.18 * logon_pressure
    risk += 0.14 * device_pressure
    risk += 0.08 * hour_pressure
    risk += 0.05 * session_pressure
    risk += 0.06 * model_pressure
    if profile.is_privileged:
        risk += 0.04
    if features["night_activity_flag"]:
        risk += 0.03

    if profile.anomaly_pattern == "night_spike" and window["timestamp"].date() >= date(2026, 3, 24):
        risk += 0.35
    if profile.anomaly_pattern == "burst_login" and window["logons"] >= profile.base_logons + 8:
        risk += 0.38
    if profile.anomaly_pattern == "device_spread" and window["devices"] >= profile.base_devices + 4:
        risk += 0.36
    if (
        profile.anomaly_pattern == "weekend_admin"
        and window["timestamp"].weekday() >= 5
        and profile.is_privileged
    ):
        risk += 0.34

    risk = max(0.03, min(risk, 0.95))
    anomaly_flag = risk >= 0.62
    return anomaly_flag, risk


def main():
    profiles = build_user_profiles()
    days = workdays_between(DEMO_START, DEMO_END)
    primary_demo_user_id = profiles[0].user_id

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Check if users already exist in the database. If so, skip seeding to save boot time.
        cur.execute("SELECT COUNT(*) FROM core.users;")
        user_count = cur.fetchone()[0]
        if user_count > 0:
            print("Database already contains seeded users. Skipping demo data seeding.")
            cur.close()
            conn.close()
            return

        ensure_monthly_partitions(cur)

        demo_employee_ids = [profile.employee_id for profile in profiles]
        cur.execute(
            "SELECT user_id::text FROM core.users WHERE employee_id = ANY(%s)",
            (demo_employee_ids,),
        )
        existing_demo_user_ids = [row[0] for row in cur.fetchall()]

        if existing_demo_user_ids:
            cur.execute("DELETE FROM security.alerts WHERE user_id = ANY(%s::uuid[])", (existing_demo_user_ids,))
            cur.execute("DELETE FROM security.risk_scores WHERE user_id = ANY(%s::uuid[])", (existing_demo_user_ids,))
            cur.execute("DELETE FROM features.user_behavior_features WHERE user_id = ANY(%s::uuid[])", (existing_demo_user_ids,))
            cur.execute("DELETE FROM events.login_events WHERE user_id = ANY(%s::uuid[])", (existing_demo_user_ids,))
            cur.execute("DELETE FROM core.devices WHERE assigned_user_id = ANY(%s::uuid[])", (existing_demo_user_ids,))
        cur.execute("DELETE FROM core.users WHERE employee_id = ANY(%s)", (demo_employee_ids,))

        department_rows = [(stable_uuid(f"dept:{name}"), name) for name in DEPARTMENTS]
        execute_values(
            cur,
            """
            INSERT INTO core.departments (department_id, department_name)
            VALUES %s
            ON CONFLICT (department_name) DO UPDATE
            SET department_name = EXCLUDED.department_name
            """,
            department_rows,
        )
        department_ids = {name: dept_id for dept_id, name in department_rows}

        role_rows = [(stable_uuid(f"role:{name}"), name) for name in ROLES]
        execute_values(
            cur,
            """
            INSERT INTO core.roles (role_id, role_name)
            VALUES %s
            ON CONFLICT (role_name) DO UPDATE
            SET role_name = EXCLUDED.role_name
            """,
            role_rows,
        )
        role_ids = {name: role_id for role_id, name in role_rows}

        user_rows = [
            (
                profile.user_id,
                profile.employee_id,
                profile.full_name,
                profile.email,
                department_ids[profile.department],
                role_ids[profile.role],
                profile.hire_date,
                profile.status,
            )
            for profile in profiles
        ]
        execute_values(
            cur,
            """
            INSERT INTO core.users (
                user_id, employee_id, full_name, email, department_id, role_id, hire_date, status
            )
            VALUES %s
            ON CONFLICT (user_id) DO UPDATE SET
                employee_id = EXCLUDED.employee_id,
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                department_id = EXCLUDED.department_id,
                role_id = EXCLUDED.role_id,
                hire_date = EXCLUDED.hire_date,
                status = EXCLUDED.status
            """,
            user_rows,
        )

        device_rows = []
        for profile in profiles:
            assigned_count = 1 if profile.base_devices == 1 else 2
            if profile.role == "Sales Executive":
                assigned_count = 2
            for device_index in range(assigned_count):
                device_name = f"{profile.employee_id}-LAP-{device_index + 1}"
                device_type = "Laptop" if device_index == 0 else "Mobile"
                device_rows.append(
                    (
                        stable_uuid(f"device:{device_name}"),
                        device_name,
                        device_type,
                        profile.user_id,
                    )
                )

        execute_values(
            cur,
            """
            INSERT INTO core.devices (device_id, device_name, device_type, assigned_user_id)
            VALUES %s
            ON CONFLICT (device_id) DO UPDATE SET
                device_name = EXCLUDED.device_name,
                device_type = EXCLUDED.device_type,
                assigned_user_id = EXCLUDED.assigned_user_id
            """,
            device_rows,
        )

        device_lookup: dict[str, list[str]] = defaultdict(list)
        for device_id, device_name, _device_type, assigned_user_id in device_rows:
            device_lookup[assigned_user_id].append(device_id)

        login_event_rows = []
        feature_rows = []
        risk_rows = []
        alert_rows = []
        alert_day_tracker: set[tuple[str, date]] = set()
        history_by_user: dict[str, list[dict]] = defaultdict(list)
        latest_high_risk_event: dict[str, datetime] = {}
        open_alert_users: set[str] = set()

        for profile in profiles:
            for day_value in days:
                windows = build_user_windows(profile, day_value)
                for window in windows:
                    event_time: datetime = window["timestamp"]
                    event_payload = {
                        "timestamp": event_time.isoformat(),
                        "logons": window["logons"],
                        "devices": window["devices"],
                    }
                    user_history = history_by_user[profile.user_id]
                    history_payload = {
                        "logon_counts": [row["logons"] for row in user_history],
                        "unique_pcs_history": [row["devices"] for row in user_history],
                        "past_logins": [row["timestamp"] for row in user_history],
                        "current_logon_count": window["logons"],
                        "current_unique_pcs": window["devices"],
                        "current_logoff_count": 0,
                    }
                    features = _compute_seed_features(event_payload, history_payload)
                    features["night_activity_flag"] = bool(features["night_activity_flag"])

                    _model_flag, anomaly_score = predict(features)
                    anomaly_flag, aggregated_risk = derive_demo_risk(profile, window, features, anomaly_score)
                    is_high_risk = aggregated_risk >= 0.72

                    assigned_devices = device_lookup.get(profile.user_id, [])
                    if not assigned_devices:
                        assigned_devices = [None]
                    for login_index in range(window["logons"]):
                        device_id = assigned_devices[min(login_index, len(assigned_devices) - 1)]
                        ip_octet = 20 + ((login_index + len(profile.employee_id)) % 200)
                        login_event_rows.append(
                            (
                                profile.user_id,
                                event_time,
                                "SUCCESS",
                                f"10.0.{(login_index % 10) + 1}.{ip_octet}",
                                device_id,
                            )
                        )

                    feature_rows.append(
                        (
                            profile.user_id,
                            event_time.date(),
                            event_time,
                            int(window["logons"]),
                            0,
                            int(window["devices"]),
                            int(event_time.hour),
                            features["z_logon"],
                            features["z_pcs"],
                            features["logon_deviation"],
                            features["device_deviation"],
                            features["device_ratio"],
                            features["burst_score"],
                            features["hour_deviation"],
                            features["session_gap"],
                            features["logon_logoff_ratio"],
                            features["night_activity_flag"],
                        )
                    )

                    risk_rows.append(
                        (
                            profile.user_id,
                            event_time.date(),
                            event_time,
                            _determine_shift(event_time.hour),
                            profile.role.lower().strip(),
                            0,
                            0,
                            False,
                            anomaly_score,
                            aggregated_risk,
                            "HIGH" if is_high_risk else "LOW",
                            bool(anomaly_flag),
                            bool(is_high_risk),
                            json.dumps(features),
                            1.0,
                            bool(anomaly_flag),
                        )
                    )

                    alert_day_key = (profile.user_id, event_time.date())
                    if is_high_risk and alert_day_key not in alert_day_tracker:
                        latest_high_risk_event[profile.user_id] = event_time
                        alert_status = classify_alert_status(event_time)
                        if alert_status == "OPEN" and profile.user_id in open_alert_users:
                            pass
                        else:
                            alert_rows.append(
                                (
                                    profile.user_id,
                                    None,
                                    "HIGH",
                                    alert_status,
                                    event_time,
                                )
                            )
                            alert_day_tracker.add(alert_day_key)
                            if alert_status == "OPEN":
                                open_alert_users.add(profile.user_id)

                    user_history.append(
                        {
                            "timestamp": event_time.isoformat(),
                            "logons": window["logons"],
                            "devices": window["devices"],
                        }
                    )

        if primary_demo_user_id not in open_alert_users and primary_demo_user_id in latest_high_risk_event:
            alert_rows.append(
                (
                    primary_demo_user_id,
                    None,
                    "HIGH",
                    "OPEN",
                    latest_high_risk_event[primary_demo_user_id] + timedelta(hours=1),
                )
            )

        execute_values(
            cur,
            """
            INSERT INTO events.login_events (
                user_id, event_timestamp, login_status, ip_address, device_id
            )
            VALUES %s
            """,
            login_event_rows,
            page_size=1000,
        )

        execute_values(
            cur,
            """
            INSERT INTO features.user_behavior_features (
                user_id, batch_date, window_start, logon_count, logoff_count, unique_pcs, hour,
                z_logon, z_pcs, logon_deviation, device_deviation, device_ratio, burst_score,
                hour_deviation, session_gap, logon_logoff_ratio, night_activity_flag
            )
            VALUES %s
            """,
            feature_rows,
            page_size=1000,
        )

        execute_values(
            cur,
            """
            INSERT INTO security.risk_scores (
                user_id, batch_date, window_start, shift, role_group,
                cluster_id, hdbscan_label, is_noise, if_score, risk_score,
                risk_level, anomaly_flag, alert_flag, feature_vector,
                cluster_probability, if_anomaly
            )
            VALUES %s
            """,
            risk_rows,
            page_size=1000,
        )

        execute_values(
            cur,
            """
            INSERT INTO security.alerts (
                user_id, risk_score_id, severity, status, created_at
            )
            VALUES %s
            """,
            alert_rows,
            page_size=500,
        )

        conn.commit()

        print(f"Seeded {len(profiles)} users")
        print(f"Inserted {len(device_rows)} devices")
        print(f"Inserted {len(login_event_rows)} login events")
        print(f"Inserted {len(feature_rows)} feature rows")
        print(f"Inserted {len(risk_rows)} risk rows")
        print(f"Inserted {len(alert_rows)} alerts")

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
