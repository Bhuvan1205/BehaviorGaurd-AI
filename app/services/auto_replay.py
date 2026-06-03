"""
auto_replay.py — Fully autonomous background event generator for BehaviorGuard-AI.

Runs as an asyncio Task inside the Uvicorn process.  Every 1–3 seconds it:
  1. Automatically selects a random scenario phase (normal / burst_alert /
     night_intrusion / device_spread) — no manual input required.
  2. Picks a random active user.
  3. Generates a realistic login event shaped by the chosen scenario.
  4. Runs the full ML pipeline in a thread-pool executor (non-blocking).
  5. Writes results to PostgreSQL.
  6. Publishes directly to the SSE StreamEngine so browsers update live.

Scenario rotation logic
-----------------------
The generator maintains an internal "phase" that automatically switches on a
configurable cadence:
  - Each phase lasts PHASE_DURATION_EVENTS events (default 40).
  - After every phase the next scenario is picked from a weighted pool so the
    demo naturally cycles through all threat types without user interaction.

Weights (out of 100):
  normal          → 45 %   (baseline calm period between attacks)
  burst_alert     → 20 %   (sudden credential-stuffing spike)
  night_intrusion → 17 %   (off-hours privileged access)
  device_spread   → 18 %   (credentials shared across many devices)

Lifecycle
---------
    from app.services.auto_replay import auto_replay_engine
    await auto_replay_engine.start()   # FastAPI startup
    await auto_replay_engine.stop()    # FastAPI shutdown
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Optional

from app.api.db import get_cursor
from app.config import ANOMALY_FLAG_THRESHOLD, RISK_THRESHOLD
from app.services.feature_engine import compute_features
from app.services.model_service import anomaly_score_to_risk, predict
from app.services.stream_engine import stream_engine

logger = logging.getLogger(__name__)

# ── Timing ────────────────────────────────────────────────────────────────────

MIN_INTERVAL = 1.5   # seconds between events (min)
MAX_INTERVAL = 3.5   # seconds between events (max)
USER_CACHE_TTL = 300  # seconds before user list is refreshed from DB

# How many events each scenario phase lasts before auto-switching
PHASE_DURATION_EVENTS = 40

# ── Scenario pool (weighted) ──────────────────────────────────────────────────

# Each entry: (scenario_name, weight)
SCENARIO_POOL = [
    ("normal",          45),
    ("burst_alert",     20),
    ("night_intrusion", 17),
    ("device_spread",   18),
]

_SCENARIO_NAMES   = [s[0] for s in SCENARIO_POOL]
_SCENARIO_WEIGHTS = [s[1] for s in SCENARIO_POOL]

# Per-scenario event generation parameters
SCENARIO_CONFIG: dict[str, dict] = {
    "normal": {
        # All events are clean baseline events
        "anomaly_prob": 0.0,
    },
    "burst_alert": {
        # ~35% of events in this phase are high-volume credential-stuffing hits
        "anomaly_prob": 0.35,
        "burst_logons":  (10, 20),
        "burst_devices": (8, 15),
        "external_ip":   True,     # traffic comes from external IP
    },
    "night_intrusion": {
        # ~35% of events are timestamped to 00:00–04:00
        "anomaly_prob": 0.35,
        "night_hours":   (0, 4),
        "burst_logons":  (5, 10),
        "burst_devices": (2, 4),
    },
    "device_spread": {
        # ~35% of events show suspicious device proliferation
        "anomaly_prob": 0.35,
        "burst_logons":  (3, 6),
        "burst_devices": (5, 8),
    },
}


# ── Risk helpers ───────────────────────────────────────────────────────────────

def _resolve_risk_level(risk_value: float) -> str:
    if risk_value >= 0.8:   return "HIGH"
    if risk_value >= 0.68:  return "ELEVATED"
    if risk_value >= 0.5:   return "GUARDED"
    return "LOW"


def _random_internal_ip() -> str:
    return f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"


def _random_external_ip() -> str:
    return f"185.{random.randint(10, 250)}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def _pick_scenario() -> str:
    """Randomly pick the next scenario using the weighted pool."""
    return random.choices(_SCENARIO_NAMES, weights=_SCENARIO_WEIGHTS, k=1)[0]


def _make_payload(user: dict, scenario: str) -> dict:
    """Build a randomised login-event payload for the given scenario."""
    cfg = SCENARIO_CONFIG.get(scenario, SCENARIO_CONFIG["normal"])
    is_anomaly = random.random() < cfg.get("anomaly_prob", 0.0)
    now = datetime.utcnow()

    if is_anomaly and scenario == "night_intrusion":
        lo, hi = cfg.get("night_hours", (0, 4))
        ts = now.replace(
            hour=random.randint(lo, hi),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
            microsecond=0,
        )
    else:
        ts = now

    if is_anomaly:
        lo, hi   = cfg.get("burst_logons",  (2, 5))
        dlo, dhi = cfg.get("burst_devices", (2, 4))
        logons  = random.randint(lo, hi)
        devices = random.randint(dlo, dhi)
        ip      = _random_external_ip() if cfg.get("external_ip") else _random_internal_ip()
        source  = "replay_anomaly"
    else:
        logons  = random.randint(1, 3)
        devices = 1
        ip      = _random_internal_ip()
        source  = "auto_replay"

    return {
        "user_id":    user["user_id"],
        "timestamp":  ts.isoformat(),
        "logons":     logons,
        "devices":    devices,
        "ip_address": ip,
        "source":     source,
        "scenario":   scenario,   # informational — included in SSE payload
    }


# ── Sync DB helpers (run in thread pool) ──────────────────────────────────────

def _load_users_sync() -> list[dict]:
    conn, cur = get_cursor()
    try:
        cur.execute(
            """
            SELECT u.user_id, u.full_name, u.employee_id,
                   d.department_name, ro.role_name
            FROM core.users u
            LEFT JOIN core.departments d  ON d.department_id = u.department_id
            LEFT JOIN core.roles       ro ON ro.role_id      = u.role_id
            WHERE u.status = 'active'
            """
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def _process_event_sync(payload: dict) -> dict:
    """
    Full ML pipeline + DB write for one event.
    Returns the scored result dict ready for SSE publication.
    Runs in a thread-pool executor — never blocks the event loop.
    """
    from datetime import date as _date

    conn, cur = get_cursor()
    try:
        user_id   = payload["user_id"]
        timestamp = payload["timestamp"]

        # ── Verify user ──────────────────────────────────────────────────────
        cur.execute("SELECT 1 FROM core.users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            raise ValueError(f"User {user_id!r} not found")

        # ── Ensure monthly partitions ────────────────────────────────────────
        event_dt    = datetime.fromisoformat(timestamp)
        month_start = event_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month  = (
            month_start.replace(year=month_start.year + 1, month=1)
            if month_start.month == 12
            else month_start.replace(month=month_start.month + 1)
        )
        suffix    = month_start.strftime("%Y_%m")
        start_lit = month_start.strftime("%Y-%m-%d")
        end_lit   = next_month.strftime("%Y-%m-%d")

        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS features.user_behavior_features_{suffix}
            PARTITION OF features.user_behavior_features
            FOR VALUES FROM ('{start_lit}') TO ('{end_lit}')
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS security.risk_scores_{suffix}
            PARTITION OF security.risk_scores_new
            FOR VALUES FROM ('{start_lit}') TO ('{end_lit}')
            """
        )

        # ── Build behavioral history from DB ─────────────────────────────────
        cur.execute(
            """
            SELECT event_timestamp, feature_vector
            FROM security.risk_scores_new
            WHERE user_id = %s
            ORDER BY event_timestamp DESC
            LIMIT 20
            """,
            (user_id,),
        )
        history_rows = cur.fetchall()
        logon_counts, device_counts, past_logins = [], [], []
        for row in reversed(history_rows):
            fv = row["feature_vector"]
            if isinstance(fv, str):
                fv = json.loads(fv)
            logon_counts.append(max(1, int(round(fv.get("logon_deviation", 0) + 2))))
            device_counts.append(max(1, int(round(fv.get("device_deviation", 0) + 1))))
            past_logins.append(str(row["event_timestamp"]))

        user_history = {
            "logon_counts":        logon_counts,
            "unique_pcs_history":  device_counts,
            "past_logins":         past_logins,
            "current_logon_count": payload["logons"],
            "current_unique_pcs":  payload["devices"],
            "current_logoff_count": 0,
        }

        # ── Feature engineering + ML ─────────────────────────────────────────
        raw_features = compute_features(
            {"timestamp": timestamp, "logons": payload["logons"], "devices": payload["devices"]},
            user_history,
        )
        features = {k: (v if v is not None else 0) for k, v in raw_features.items()}
        features["night_activity_flag"] = bool(features.get("night_activity_flag", False))

        _, anomaly_score = predict(features)
        risk_value   = anomaly_score_to_risk(anomaly_score)
        anomaly_flag = risk_value >= ANOMALY_FLAG_THRESHOLD
        risk_level   = _resolve_risk_level(risk_value)
        is_high_risk = risk_value >= RISK_THRESHOLD

        # ── Persist events ───────────────────────────────────────────────────
        cur.execute(
            """
            INSERT INTO events.login_events
            (user_id, event_timestamp, login_status, ip_address, device_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, timestamp, "SUCCESS", payload["ip_address"], None),
        )
        cur.execute(
            "DELETE FROM features.user_behavior_features WHERE user_id = %s AND window_start = %s",
            (user_id, timestamp),
        )
        cur.execute(
            """
            INSERT INTO features.user_behavior_features (
                user_id, window_start, z_logon, z_pcs, logon_deviation, device_deviation,
                device_ratio, burst_score, hour_deviation, session_gap, logon_logoff_ratio,
                night_activity_flag
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id, timestamp,
                features["z_logon"], features["z_pcs"],
                features["logon_deviation"], features["device_deviation"],
                features["device_ratio"], features["burst_score"],
                features["hour_deviation"], features["session_gap"],
                features["logon_logoff_ratio"], features["night_activity_flag"],
            ),
        )
        cur.execute(
            """
            INSERT INTO security.risk_scores_new (
                user_id, anomaly_score, anomaly_flag, risk_score, risk_level,
                alert_flag, event_timestamp, model_version_id, feature_vector, window_start
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id, float(anomaly_score), bool(anomaly_flag),
                risk_value, risk_level, is_high_risk, timestamp,
                "if_v1_standard_scaler", json.dumps(features), timestamp,
            ),
        )

        created_alert = False
        if is_high_risk:
            cur.execute(
                """
                INSERT INTO security.alerts (user_id, risk_score_id, severity, status)
                SELECT %s, NULL, 'HIGH', 'OPEN'
                WHERE NOT EXISTS (
                    SELECT 1 FROM security.alerts WHERE user_id = %s AND status = 'OPEN'
                )
                """,
                (user_id, user_id),
            )
            created_alert = cur.rowcount > 0

        conn.commit()

        # ── Fetch user metadata for SSE payload ──────────────────────────────
        cur.execute(
            """
            SELECT u.full_name, u.employee_id, d.department_name, r.role_name
            FROM core.users u
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles       r ON r.role_id       = u.role_id
            WHERE u.user_id = %s
            """,
            (user_id,),
        )
        meta = cur.fetchone() or {}

        return {
            "type":               "scored_event",
            "user_id":            user_id,
            "full_name":          meta.get("full_name", "Unknown"),
            "employee_id":        meta.get("employee_id", ""),
            "department":         meta.get("department_name", ""),
            "role":               meta.get("role_name", ""),
            # Append "Z" so JavaScript treats this as UTC and toLocaleTimeString()
            # correctly converts it to the user's local timezone for display.
            "timestamp":          timestamp + "Z",
            "source":             payload["source"],
            "scenario":           payload.get("scenario", "normal"),
            "logons":             payload["logons"],
            "devices":            payload["devices"],
            "ip_address":         payload["ip_address"],
            "anomaly_flag":       bool(anomaly_flag),
            "anomaly_score":      float(anomaly_score),
            "risk_score":         risk_value,
            "risk_level":         risk_level,
            "alert_created":      created_alert,
            # ML feature vector — included for the AlertsPage event detail drawer
            "features":           features,
            # Top-level convenience fields used directly by some UI components
            "z_logon":            features.get("z_logon"),
            "z_pcs":              features.get("z_pcs"),
            "logon_deviation":    features.get("logon_deviation"),
            "device_deviation":   features.get("device_deviation"),
            "device_ratio":       features.get("device_ratio"),
            "burst_score":        features.get("burst_score"),
            "hour_deviation":     features.get("hour_deviation"),
            "session_gap":        features.get("session_gap"),
            "logon_logoff_ratio": features.get("logon_logoff_ratio"),
            "night_activity_flag": features.get("night_activity_flag", False),
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ── Engine ────────────────────────────────────────────────────────────────────

class AutoReplayEngine:
    """
    Fully autonomous event generator.

    Internally rotates through all scenario types on a configurable cadence
    using weighted random selection.  No external input or manual scenario
    selection is ever required.
    """

    def __init__(self) -> None:
        self._stop_event: asyncio.Event | None = None
        self._task: Optional[asyncio.Task]     = None
        self._users: list[dict]                = []
        self._users_loaded_at: Optional[datetime] = None

        # Phase tracking — auto-rotates every PHASE_DURATION_EVENTS events
        self._current_scenario: str = _pick_scenario()
        self._phase_events_remaining: int = PHASE_DURATION_EVENTS

    # ── Public status (read-only) ──────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "current_scenario":        self._current_scenario,
            "phase_events_remaining":  self._phase_events_remaining,
            "phase_duration":          PHASE_DURATION_EVENTS,
        }

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._loop(), name="auto_replay")
        logger.info("AutoReplayEngine started (fully autonomous mode).")

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        logger.info("AutoReplayEngine stopped.")

    # ── Internal loop ─────────────────────────────────────────────────────

    async def _loop(self) -> None:
        await asyncio.sleep(3.0)  # wait for server to fully start
        loop = asyncio.get_event_loop()

        while not self._stop_event.is_set():
            try:
                await self._tick(loop)
            except Exception as exc:
                logger.warning("AutoReplay tick error: %s", exc)

            interval = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _refresh_users(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            users = await loop.run_in_executor(None, _load_users_sync)
            if users:
                self._users = users
                self._users_loaded_at = datetime.utcnow()
                logger.info("AutoReplay: %d active users loaded.", len(users))
        except Exception as exc:
            logger.warning("AutoReplay: user refresh failed: %s", exc)

    def _advance_phase(self) -> None:
        """Decrement phase counter and rotate to a new scenario when exhausted."""
        self._phase_events_remaining -= 1
        if self._phase_events_remaining <= 0:
            old = self._current_scenario
            self._current_scenario = _pick_scenario()
            self._phase_events_remaining = PHASE_DURATION_EVENTS
            logger.info(
                "AutoReplay: scenario rotated  %s → %s  (next %d events)",
                old, self._current_scenario, PHASE_DURATION_EVENTS,
            )

    async def _tick(self, loop: asyncio.AbstractEventLoop) -> None:
        # Refresh user cache if stale
        stale = (
            not self._users_loaded_at
            or (datetime.utcnow() - self._users_loaded_at).total_seconds() > USER_CACHE_TTL
        )
        if not self._users or stale:
            await self._refresh_users()

        if not self._users:
            return

        # Auto-rotate scenario before building the payload
        self._advance_phase()

        user    = random.choice(self._users)
        payload = _make_payload(user, self._current_scenario)

        # Run ML pipeline + DB write in thread (non-blocking)
        result = await loop.run_in_executor(None, _process_event_sync, payload)

        # Publish directly to SSE bus — we are ON the event loop
        await stream_engine.publish(result)

        logger.debug(
            "AutoReplay: %-22s | scenario=%-16s | risk=%.2f | anomaly=%s",
            result["full_name"], self._current_scenario,
            result["risk_score"], result["anomaly_flag"],
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

auto_replay_engine = AutoReplayEngine()
