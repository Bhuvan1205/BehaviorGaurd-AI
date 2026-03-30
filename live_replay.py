#!/usr/bin/env python3
"""
live_replay.py — BehaviorGuard-AI Demo / Live Replay Engine

Simulates a real corporate workday by replaying employee login events
through the /stream/ingest API endpoint in accelerated real time.

Usage
-----
    # Full workday at 60x speed (8 hrs → ~8 minutes), burst-login anomaly
    python live_replay.py --speed 60 --scenario burst_alert

    # Slow preview at 10x speed, normal day
    python live_replay.py --speed 10 --scenario normal

    # Fast demo at 120x speed, device spread attack
    python live_replay.py --speed 120 --scenario device_spread

    # Night intrusion scenario
    python live_replay.py --speed 60 --scenario night_intrusion

Arguments
---------
    --speed   N     N seconds of simulated time per 1 real second (default: 60)
    --scenario STR  Anomaly scenario: normal | burst_alert | night_intrusion
                    | device_spread (default: normal)
    --api     URL   Backend API base URL (default: http://localhost:8001)
    --token   STR   Bearer token. If omitted, auto-login with analyst/Admin@123
    --date    DATE  Simulated workday date YYYY-MM-DD (default: today)

How it works
------------
1. Fetches the list of all active users from the API.
2. Assigns each user a realistic shift pattern and login schedule.
3. Computes when each login event would occur during an 09:00–18:00 workday.
4. Sleeps until each event's "wall clock" equivalent time, then POSTs to
   /stream/ingest — which triggers the full feature engineering + ML pipeline.
5. The ML result is immediately broadcast via SSE to all connected browsers.

The anomaly scenario controls whether specific users exhibit unusual patterns
(burst logins, late-night activity, device sprawl) mid-session so the demo
dashboard clearly shows alerts firing in real time.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_API = "http://localhost:8001"
DEFAULT_SPEED = 60          # 1 simulated hour = 60 real seconds
WORKDAY_START_HOUR = 9      # 09:00
WORKDAY_END_HOUR = 18       # 18:00
ANOMALY_INJECTION_HOUR = 11 # Anomaly events fire at 11:00 sim time


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = {
    "normal": {
        "description": "Typical Tuesday — all employees log in normally, no anomalies.",
        "anomaly_users_pct": 0.0,
        "burst_logons": 2,
        "burst_devices": 1,
        "injection_hour": None,
    },
    "burst_alert": {
        "description": "A user suddenly logs in from 12 devices 15 times in a single window.",
        "anomaly_users_pct": 0.05,   # ~3 users out of 60
        "burst_logons": 15,
        "burst_devices": 12,
        "injection_hour": ANOMALY_INJECTION_HOUR,
    },
    "night_intrusion": {
        "description": "Privileged accounts active at 02:00 on a weeknight.",
        "anomaly_users_pct": 0.03,
        "burst_logons": 8,
        "burst_devices": 3,
        "injection_hour": 2,         # 02:00 sim time
    },
    "device_spread": {
        "description": "An employee's credentials used across 6 different devices.",
        "anomaly_users_pct": 0.05,
        "burst_logons": 4,
        "burst_devices": 6,
        "injection_hour": ANOMALY_INJECTION_HOUR,
    },
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LoginEvent:
    user_id: str
    full_name: str
    employee_id: str
    sim_time: datetime          # Simulated clock time this event should fire
    logons: int = 2
    devices: int = 1
    ip_address: str = "10.0.0.1"
    is_anomaly: bool = False


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str, token: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    def _auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def login(self, username: str = "analyst", password: str = "Admin@123") -> str:
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        self.token = resp.json()["token"]
        print(f"  ✓ Authenticated as '{username}'")
        return self.token

    def get_users(self) -> list[dict]:
        resp = self.session.get(
            f"{self.base_url}/users",
            headers=self._auth_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def ingest(self, event: LoginEvent) -> dict:
        payload = {
            "user_id": event.user_id,
            "timestamp": event.sim_time.isoformat(),
            "logons": event.logons,
            "devices": event.devices,
            "ip_address": event.ip_address,
            "source": "replay_anomaly" if event.is_anomaly else "live_replay",
        }
        resp = self.session.post(
            f"{self.base_url}/stream/ingest",
            json=payload,
            headers=self._auth_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def set_scenario(self, scenario: str) -> None:
        self.session.post(
            f"{self.base_url}/stream/scenario",
            json={"scenario": scenario},
            headers=self._auth_headers(),
            timeout=5,
        )

    def set_replay_status(self, running: bool) -> None:
        """Best-effort status update — engine may not expose this endpoint yet."""
        try:
            self.session.post(
                f"{self.base_url}/stream/replay-status",
                json={"running": running},
                headers=self._auth_headers(),
                timeout=3,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Event schedule builder
# ---------------------------------------------------------------------------

def build_event_schedule(
    users: list[dict],
    sim_date: date,
    scenario_cfg: dict,
    rng: random.Random,
) -> list[LoginEvent]:
    """
    Build a sorted list of LoginEvents for the simulated workday.

    Each user gets 1–3 normal login windows spread across their shift.
    Anomaly users additionally get an injected burst event at the scenario's
    injection hour.
    """
    events: list[LoginEvent] = []
    scenario_users: set[str] = set()

    # Select anomaly target users
    anomaly_pct = scenario_cfg["anomaly_users_pct"]
    if anomaly_pct > 0:
        count = max(1, math.ceil(len(users) * anomaly_pct))
        anomaly_targets = rng.sample(users, k=min(count, len(users)))
        scenario_users = {u["user_id"] for u in anomaly_targets}
        target_names = [u["full_name"] for u in anomaly_targets]
        print(f"\n  ⚠  Anomaly targets: {', '.join(target_names)}")

    for user in users:
        uid = user["user_id"]
        # Assign a shift — deterministic on employee_id hash
        shift_hash = int(uid.replace("-", ""), 16) % 6
        if shift_hash < 4:
            anchor = 9   # Day shift
        elif shift_hash < 5:
            anchor = 15  # Evening shift
        else:
            anchor = 23  # Night shift

        # Build normal login windows (1–2 per shift)
        num_windows = rng.choice([1, 2])
        for slot in range(num_windows):
            hour = min(23, anchor + slot + rng.randint(-1, 1))
            minute = rng.randint(0, 55)
            sim_dt = datetime.combine(sim_date, datetime.min.time()).replace(
                hour=hour, minute=minute, second=0
            )
            logons = user.get("avg_logons", rng.randint(1, 3))
            if isinstance(logons, float):
                logons = max(1, int(round(logons)))
            logons = max(1, logons)
            devices = 1

            ip3 = rng.randint(1, 254)
            ip4 = rng.randint(1, 254)

            events.append(LoginEvent(
                user_id=uid,
                full_name=user.get("full_name", "Unknown"),
                employee_id=user.get("employee_id", ""),
                sim_time=sim_dt,
                logons=logons,
                devices=devices,
                ip_address=f"10.0.{ip3}.{ip4}",
                is_anomaly=False,
            ))

        # Inject anomaly event for selected users
        if uid in scenario_users and scenario_cfg["injection_hour"] is not None:
            inj_hour = scenario_cfg["injection_hour"]
            inj_minute = rng.randint(3, 45)
            inj_dt = datetime.combine(sim_date, datetime.min.time()).replace(
                hour=inj_hour, minute=inj_minute, second=0
            )
            events.append(LoginEvent(
                user_id=uid,
                full_name=user.get("full_name", "Unknown"),
                employee_id=user.get("employee_id", ""),
                sim_time=inj_dt,
                logons=scenario_cfg["burst_logons"],
                devices=scenario_cfg["burst_devices"],
                ip_address=f"185.{rng.randint(10,250)}.{rng.randint(1,254)}.{rng.randint(1,254)}",
                is_anomaly=True,
            ))

    events.sort(key=lambda e: e.sim_time)
    return events


# ---------------------------------------------------------------------------
# Main replay loop
# ---------------------------------------------------------------------------

def run_replay(
    api: APIClient,
    events: list[LoginEvent],
    sim_date: date,
    speed: float,
) -> None:
    """
    Execute the event schedule in real time, sleeping between events.

    Wall clock time = simulation time / speed
    """
    total = len(events)
    processed = 0
    anomalies_fired = 0
    alerts_created = 0

    sim_start = datetime.combine(sim_date, datetime.min.time()).replace(hour=WORKDAY_START_HOUR)
    real_start = datetime.utcnow()

    print(f"\n  Simulated workday: {sim_date} {WORKDAY_START_HOUR:02d}:00 → {WORKDAY_END_HOUR:02d}:00")
    print(f"  Speed: {speed}×  ({(WORKDAY_END_HOUR - WORKDAY_START_HOUR) * 60 / speed:.1f} real minutes for full day)")
    print(f"  Total events queued: {total}\n")
    print("  ─" * 35)

    for evt in events:
        # How far into the simulated day is this event?
        sim_offset_secs = (evt.sim_time - sim_start).total_seconds()
        # What real-clock second should we fire it?
        real_offset_secs = sim_offset_secs / speed
        target_real_time = real_start + timedelta(seconds=real_offset_secs)

        # Sleep until it's time
        wait = (target_real_time - datetime.utcnow()).total_seconds()
        if wait > 0:
            time.sleep(wait)

        # Fire!
        try:
            result = api.ingest(evt)
            processed += 1
            risk = result.get("risk_score", 0)
            risk_pct = f"{int(risk * 100):>3d}%"
            flag = "⚠ ANOMALY" if result.get("anomaly_flag") else "✓ normal "
            alert_str = "  🚨 ALERT!" if result.get("alert_created") else ""

            if result.get("anomaly_flag"):
                anomalies_fired += 1
            if result.get("alert_created"):
                alerts_created += 1

            sim_time_str = evt.sim_time.strftime("%H:%M")
            name = evt.full_name[:20].ljust(20)
            print(
                f"  {sim_time_str}  {name}  risk={risk_pct}  {flag}"
                f"  logons={evt.logons:>2d}  dev={evt.devices}"
                f"{alert_str}"
            )

        except requests.HTTPError as exc:
            print(f"  ✗ {evt.full_name} @ {evt.sim_time.strftime('%H:%M')} — {exc}")
        except Exception as exc:
            print(f"  ✗ Unexpected error: {exc}")

    print("\n  ─" * 35)
    print(f"\n  Replay complete!")
    print(f"  Events processed : {processed}/{total}")
    print(f"  Anomalies fired  : {anomalies_fired}")
    print(f"  Alerts created   : {alerts_created}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BehaviorGuard-AI Live Replay Engine — demo / testing tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--speed", type=float, default=DEFAULT_SPEED,
        help=f"Simulation speed multiplier (default: {DEFAULT_SPEED}). "
             "60 = 1 simulated hour per 1 real minute.",
    )
    parser.add_argument(
        "--scenario", default="normal",
        choices=list(SCENARIOS),
        help="Anomaly scenario to inject (default: normal).",
    )
    parser.add_argument(
        "--api", default=DEFAULT_API,
        help=f"Backend API base URL (default: {DEFAULT_API}).",
    )
    parser.add_argument(
        "--token", default=None,
        help="Bearer auth token. Auto-login if omitted.",
    )
    parser.add_argument(
        "--date", default=None,
        help="Simulated date YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible schedules (default: 42).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Parse date
    if args.date:
        try:
            sim_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid date: {args.date!r}. Use YYYY-MM-DD format.", file=sys.stderr)
            sys.exit(1)
    else:
        sim_date = date.today()

    scenario_cfg = SCENARIOS[args.scenario]
    rng = random.Random(args.seed)

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   BehaviorGuard-AI  —  Live Replay Engine           ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"\n  Scenario  : {args.scenario}")
    print(f"  Summary   : {scenario_cfg['description']}")
    print(f"  Sim date  : {sim_date}")
    print(f"  Speed     : {args.speed}×")
    print(f"  API       : {args.api}")

    # Connect
    api = APIClient(base_url=args.api, token=args.token)

    if not api.token:
        print("\n  Authenticating...")
        try:
            api.login()
        except Exception as exc:
            print(f"\n  ✗ Authentication failed: {exc}", file=sys.stderr)
            print("  Make sure the backend is running and credentials are correct.", file=sys.stderr)
            sys.exit(1)

    # Register scenario with the backend
    print(f"\n  Setting backend scenario to '{args.scenario}'...")
    try:
        api.set_scenario(args.scenario)
    except Exception:
        pass  # Non-critical

    # Fetch users
    print("  Fetching active users...")
    try:
        users = api.get_users()
        print(f"  ✓ {len(users)} active users loaded")
    except Exception as exc:
        print(f"\n  ✗ Failed to load users: {exc}", file=sys.stderr)
        sys.exit(1)

    if not users:
        print("\n  ✗ No users found. Run seed_demo_data.py first.", file=sys.stderr)
        sys.exit(1)

    # Build schedule
    print("  Building event schedule...")
    events = build_event_schedule(users, sim_date, scenario_cfg, rng)
    print(f"  ✓ {len(events)} events scheduled")

    # Run
    print("\n  Starting replay... (Ctrl+C to stop)\n")
    try:
        run_replay(api, events, sim_date, args.speed)
    except KeyboardInterrupt:
        print("\n\n  Replay stopped by user.")
    finally:
        api.set_scenario("normal")  # Reset to normal on exit


if __name__ == "__main__":
    main()
