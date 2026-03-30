import asyncio
import json
import logging
import traceback
import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.db import get_cursor
from app.config import ANOMALY_FLAG_THRESHOLD, RISK_THRESHOLD
from app.services.feature_engine import compute_features
from app.services.model_service import anomaly_score_to_risk, predict
from app.services.stream_engine import stream_engine


router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resolve_risk_level(risk_value: float) -> str:
    if risk_value >= 0.8:
        return "HIGH"
    if risk_value >= 0.68:
        return "ELEVATED"
    if risk_value >= 0.5:
        return "GUARDED"
    return "LOW"





class IngestEvent(BaseModel):
    """Raw log event for real-time stream ingestion — mirrors what a
    Windows Event Log collector or SIEM would forward."""
    user_id: str
    timestamp: str
    logons: int = 1
    devices: int = 1
    ip_address: str = "10.0.0.1"
    device_name: str = ""
    source: str = "stream"  # e.g. 'windows_event', 'siem', 'replay'


class ScenarioRequest(BaseModel):
    scenario: str  # 'normal' | 'burst_alert' | 'night_intrusion' | 'device_spread'


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    employee_id: str
    full_name: str
    username: str
    password: str


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_admin_tables(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS security.admin_users (
            admin_id UUID PRIMARY KEY,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS security.admin_sessions (
            session_id UUID PRIMARY KEY,
            admin_id UUID NOT NULL REFERENCES security.admin_users(admin_id),
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
        """
    )
    cur.execute(
        """
        INSERT INTO security.admin_users (admin_id, employee_id, full_name, username, password_hash)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """,
        (
            str(uuid.uuid5(uuid.NAMESPACE_DNS, "behaviorguard-demo-admin")),
            "SEC-1001",
            "Security Demo Admin",
            "analyst",
            hash_password("Admin@123"),
        ),
    )


def get_current_admin(cur, authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    cur.execute(
        """
        SELECT
            s.session_id,
            a.admin_id,
            a.employee_id,
            a.full_name,
            a.username,
            s.expires_at,
            s.is_active
        FROM security.admin_sessions s
        JOIN security.admin_users a ON a.admin_id = s.admin_id
        WHERE s.session_token = %s
          AND s.is_active = TRUE
          AND s.expires_at > CURRENT_TIMESTAMP
        LIMIT 1
        """,
        (token,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return row


def parse_event_timestamp(timestamp: str) -> datetime:
    normalized = timestamp.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def ensure_monthly_partitions(cur, timestamp: str) -> None:
    event_dt = parse_event_timestamp(timestamp)
    month_start = event_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    next_month = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    suffix = month_start.strftime("%Y_%m")
    start_literal = month_start.strftime("%Y-%m-%d")
    end_literal = next_month.strftime("%Y-%m-%d")

    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS features.user_behavior_features_{suffix}
        PARTITION OF features.user_behavior_features
        FOR VALUES FROM ('{start_literal}') TO ('{end_literal}')
        """
    )
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS security.risk_scores_{suffix}
        PARTITION OF security.risk_scores_new
        FOR VALUES FROM ('{start_literal}') TO ('{end_literal}')
        """
    )


def fetch_latest_open_alert(cur, user_id: str):
    cur.execute(
        """
        SELECT alert_id, user_id, risk_score_id, severity, status, created_at
        FROM security.alerts
        WHERE user_id = %s AND status = 'OPEN'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,),
    )
    return cur.fetchone()


@router.post("/auth/login")
def login(data: LoginRequest):
    try:
        conn, cur = get_cursor()
        ensure_admin_tables(cur)
        cur.execute(
            """
            SELECT admin_id, employee_id, full_name, username, password_hash
            FROM security.admin_users
            WHERE username = %s
            LIMIT 1
            """,
            (data.username.strip(),),
        )
        admin = cur.fetchone()
        if not admin or admin["password_hash"] != hash_password(data.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = secrets.token_urlsafe(32)
        session_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO security.admin_sessions (session_id, admin_id, session_token, expires_at, is_active)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '12 hours', TRUE)
            """,
            (session_id, admin["admin_id"], token),
        )
        conn.commit()
        return {
            "token": token,
            "admin": {
                "admin_id": admin["admin_id"],
                "employee_id": admin["employee_id"],
                "full_name": admin["full_name"],
                "username": admin["username"],
            },
        }
    except HTTPException:
        if "conn" in locals():
            conn.rollback()
        raise
    except Exception as exc:
        if "conn" in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.post("/auth/register")
def register(data: RegisterRequest):
    try:
        conn, cur = get_cursor()
        ensure_admin_tables(cur)
        cur.execute(
            """
            INSERT INTO security.admin_users (admin_id, employee_id, full_name, username, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING admin_id, employee_id, full_name, username
            """,
            (
                str(uuid.uuid4()),
                data.employee_id.strip(),
                data.full_name.strip(),
                data.username.strip(),
                hash_password(data.password),
            ),
        )
        admin = cur.fetchone()
        conn.commit()
        return dict(admin)
    except Exception as exc:
        if "conn" in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.post("/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        admin = get_current_admin(cur, authorization)
        token = authorization.replace("Bearer ", "", 1).strip()
        cur.execute(
            """
            UPDATE security.admin_sessions
            SET is_active = FALSE
            WHERE session_token = %s AND admin_id = %s
            """,
            (token, admin["admin_id"]),
        )
        conn.commit()
        return {"success": True}
    except HTTPException:
        if "conn" in locals():
            conn.rollback()
        raise
    except Exception as exc:
        if "conn" in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/auth/me")
def me(authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        ensure_admin_tables(cur)
        admin = get_current_admin(cur, authorization)
        return {
            "admin_id": admin["admin_id"],
            "employee_id": admin["employee_id"],
            "full_name": admin["full_name"],
            "username": admin["username"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/users")
def get_users(authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        cur.execute(
            """
            WITH latest_risk AS (
                SELECT DISTINCT ON (r.user_id)
                    r.user_id,
                    r.risk_score AS latest_risk,
                    r.risk_level AS latest_risk_level,
                    r.event_timestamp AS latest_event_timestamp
                FROM security.risk_scores_new r
                ORDER BY r.user_id, r.event_timestamp DESC
            ),
            risk_stats AS (
                SELECT
                    r.user_id,
                    AVG(r.risk_score) AS avg_risk,
                    COUNT(*) AS history_count,
                    SUM(CASE WHEN r.anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
                FROM security.risk_scores_new r
                GROUP BY r.user_id
            ),
            alert_stats AS (
                SELECT
                    a.user_id,
                    COUNT(*) AS alert_count,
                    SUM(CASE WHEN a.status = 'OPEN' THEN 1 ELSE 0 END) AS open_alert_count
                FROM security.alerts a
                GROUP BY a.user_id
            )
            SELECT
                u.user_id,
                u.employee_id,
                u.full_name,
                u.email,
                u.status,
                u.hire_date,
                d.department_name,
                rl.role_name,
                COALESCE(lr.latest_risk, 0) AS latest_risk,
                COALESCE(lr.latest_risk_level, 'LOW') AS latest_risk_level,
                lr.latest_event_timestamp,
                COALESCE(rs.avg_risk, 0) AS avg_risk,
                COALESCE(rs.history_count, 0) AS history_count,
                COALESCE(rs.anomaly_count, 0) AS anomaly_count,
                COALESCE(al.alert_count, 0) AS alert_count,
                COALESCE(al.open_alert_count, 0) AS open_alert_count
            FROM core.users u
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles rl ON rl.role_id = u.role_id
            LEFT JOIN latest_risk lr ON lr.user_id = u.user_id
            LEFT JOIN risk_stats rs ON rs.user_id = u.user_id
            LEFT JOIN alert_stats al ON al.user_id = u.user_id
            WHERE u.status = 'active'
            ORDER BY
                COALESCE(al.open_alert_count, 0) DESC,
                COALESCE(lr.latest_risk, 0) DESC,
                COALESCE(rs.avg_risk, 0) DESC,
                u.full_name ASC
            """
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/users/{user_id}")
def get_user_detail(user_id: str, authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        cur.execute(
            """
            WITH latest_risk AS (
                SELECT DISTINCT ON (r.user_id)
                    r.user_id,
                    r.risk_score AS latest_risk,
                    r.risk_level AS latest_risk_level,
                    r.event_timestamp AS latest_event_timestamp
                FROM security.risk_scores_new r
                WHERE r.user_id = %s
                ORDER BY r.user_id, r.event_timestamp DESC
            ),
            risk_stats AS (
                SELECT
                    r.user_id,
                    AVG(r.risk_score) AS avg_risk,
                    COUNT(*) AS history_count,
                    SUM(CASE WHEN r.anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
                FROM security.risk_scores_new r
                WHERE r.user_id = %s
                GROUP BY r.user_id
            ),
            alert_stats AS (
                SELECT
                    a.user_id,
                    COUNT(*) AS alert_count,
                    SUM(CASE WHEN a.status = 'OPEN' THEN 1 ELSE 0 END) AS open_alert_count
                FROM security.alerts a
                WHERE a.user_id = %s
                GROUP BY a.user_id
            )
            SELECT
                u.user_id,
                u.employee_id,
                u.full_name,
                u.email,
                u.status,
                u.hire_date,
                d.department_name,
                rl.role_name,
                COALESCE(lr.latest_risk, 0) AS latest_risk,
                COALESCE(lr.latest_risk_level, 'LOW') AS latest_risk_level,
                lr.latest_event_timestamp,
                COALESCE(rs.avg_risk, 0) AS avg_risk,
                COALESCE(rs.history_count, 0) AS history_count,
                COALESCE(rs.anomaly_count, 0) AS anomaly_count,
                COALESCE(al.alert_count, 0) AS alert_count,
                COALESCE(al.open_alert_count, 0) AS open_alert_count
            FROM core.users u
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles rl ON rl.role_id = u.role_id
            LEFT JOIN latest_risk lr ON lr.user_id = u.user_id
            LEFT JOIN risk_stats rs ON rs.user_id = u.user_id
            LEFT JOIN alert_stats al ON al.user_id = u.user_id
            WHERE u.user_id = %s
            LIMIT 1
            """,
            (user_id, user_id, user_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/dashboard/summary")
def get_dashboard_summary(authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        cur.execute(
            """
            WITH org_metrics AS (
                SELECT
                    (SELECT COUNT(*) FROM core.users WHERE status = 'active') AS active_users,
                    (SELECT COUNT(*) FROM core.departments) AS departments,
                    (SELECT COUNT(*) FROM core.devices) AS devices,
                    (SELECT COUNT(*) FROM events.login_events) AS login_events,
                    (SELECT COUNT(*) FROM security.alerts) AS alerts_total,
                    (SELECT COUNT(*) FROM security.alerts WHERE status = 'OPEN') AS alerts_open,
                    (SELECT COALESCE(AVG(risk_score), 0) FROM security.risk_scores_new) AS avg_risk,
                    (SELECT COUNT(*) FROM security.risk_scores_new WHERE risk_score >= %s) AS high_risk_windows
            ),
            risk_bands AS (
                SELECT
                    CASE
                        WHEN risk_score < 0.25 THEN 'Low'
                        WHEN risk_score < 0.50 THEN 'Guarded'
                        WHEN risk_score < %s THEN 'Elevated'
                        ELSE 'High'
                    END AS band,
                    COUNT(*) AS count
                FROM security.risk_scores_new
                GROUP BY 1
            ),
            user_risk AS (
                SELECT
                    u.user_id,
                    u.full_name,
                    u.employee_id,
                    d.department_name,
                    rl.role_name,
                    COALESCE(MAX(r.risk_score), 0) AS max_risk,
                    COALESCE(AVG(r.risk_score), 0) AS avg_risk
                FROM core.users u
                LEFT JOIN core.departments d ON d.department_id = u.department_id
                LEFT JOIN core.roles rl ON rl.role_id = u.role_id
                LEFT JOIN security.risk_scores_new r ON r.user_id = u.user_id
                WHERE u.status = 'active'
                GROUP BY u.user_id, u.full_name, u.employee_id, d.department_name, rl.role_name
            ),
            user_alerts AS (
                SELECT
                    a.user_id,
                    COUNT(*) AS alert_count,
                    SUM(CASE WHEN a.status = 'OPEN' THEN 1 ELSE 0 END) AS open_alert_count
                FROM security.alerts a
                GROUP BY a.user_id
            ),
            user_rollup AS (
                SELECT
                    ur.user_id,
                    ur.full_name,
                    ur.employee_id,
                    ur.department_name,
                    ur.role_name,
                    ur.max_risk,
                    ur.avg_risk,
                    COALESCE(ua.alert_count, 0) AS alert_count,
                    COALESCE(ua.open_alert_count, 0) AS open_alert_count
                FROM user_risk ur
                LEFT JOIN user_alerts ua ON ua.user_id = ur.user_id
            ),
            top_users AS (
                SELECT
                    user_id,
                    full_name,
                    employee_id,
                    department_name,
                    role_name,
                    max_risk,
                    avg_risk,
                    open_alert_count
                FROM user_rollup
                ORDER BY open_alert_count DESC, max_risk DESC, avg_risk DESC, full_name
                LIMIT 8
            ),
            recent_alerts AS (
                SELECT
                    a.alert_id,
                    a.user_id,
                    u.full_name,
                    u.employee_id,
                    a.severity,
                    a.status,
                    a.created_at
                FROM security.alerts a
                JOIN core.users u ON u.user_id = a.user_id
                ORDER BY a.created_at DESC
                LIMIT 8
            ),
            dept_rollup AS (
                SELECT
                    department_name,
                    COUNT(*) AS user_count,
                    COALESCE(AVG(avg_risk), 0) AS avg_risk,
                    COALESCE(SUM(open_alert_count), 0) AS open_alert_count
                FROM user_rollup
                GROUP BY department_name
                ORDER BY avg_risk DESC, open_alert_count DESC, department_name
                LIMIT 8
            )
            SELECT json_build_object(
                'totals', (SELECT row_to_json(org_metrics) FROM org_metrics),
                'risk_distribution', (SELECT COALESCE(json_agg(risk_bands ORDER BY band), '[]'::json) FROM risk_bands),
                'top_users', (SELECT COALESCE(json_agg(top_users), '[]'::json) FROM top_users),
                'recent_alerts', (SELECT COALESCE(json_agg(recent_alerts), '[]'::json) FROM recent_alerts),
                'department_rollup', (SELECT COALESCE(json_agg(dept_rollup), '[]'::json) FROM dept_rollup)
            ) AS payload
            """,
            (RISK_THRESHOLD, RISK_THRESHOLD),
        )
        return cur.fetchone()["payload"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()





@router.get("/history")
def get_history(user_id: str, authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        cur.execute(
            """
            WITH event_rollup AS (
                SELECT
                    user_id,
                    event_timestamp,
                    COUNT(*) AS logon_count,
                    COUNT(DISTINCT COALESCE(device_id::text, 'unknown')) AS device_count
                FROM events.login_events
                WHERE user_id = %s
                GROUP BY user_id, event_timestamp
            )
            SELECT r.score_id, r.anomaly_score, r.anomaly_flag, r.risk_score, r.risk_level,
                   r.alert_flag, r.event_timestamp, r.model_version_id, r.window_start, r.created_at,
                   r.feature_vector, COALESCE(e.logon_count, 0) AS logon_count,
                   COALESCE(e.device_count, 0) AS device_count
            FROM security.risk_scores_new r
            LEFT JOIN event_rollup e
              ON e.user_id = r.user_id AND e.event_timestamp = r.event_timestamp
            WHERE r.user_id = %s
            ORDER BY event_timestamp DESC
            LIMIT 100
            """,
            (user_id, user_id),
        )
        return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/alerts")
def get_alerts(user_id: str, authorization: Optional[str] = Header(default=None)):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        cur.execute(
            """
            SELECT alert_id, user_id, risk_score_id, severity, status, created_at
            FROM security.alerts
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


# ---------------------------------------------------------------------------
# REAL-TIME STREAMING ENDPOINTS
# ---------------------------------------------------------------------------


@router.post("/stream/ingest")
def stream_ingest(data: IngestEvent, authorization: Optional[str] = Header(default=None)):
    """
    Ingest a raw log event and immediately run the full ML pipeline.

    This is the primary ingestion endpoint for real-time sources:
    Windows Event Log collectors, SIEMs, EDR agents, or the live_replay.py
    demo engine.  The scored result is published to all connected SSE clients.

    No manual history is required — the system pulls the last 20 events
    from the database automatically to build the behavioral baseline.
    """
    try:
        conn, cur = get_cursor()

        # --- Auth (optional for internal ingest; replay engine passes token) ---
        if authorization and authorization.startswith("Bearer "):
            get_current_admin(cur, authorization)

        # --- Verify user exists ---
        cur.execute("SELECT 1 FROM core.users WHERE user_id = %s", (data.user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"User {data.user_id!r} not found")

        # --- Ensure DB partitions exist for this timestamp ---
        ensure_monthly_partitions(cur, data.timestamp)

        # --- Build behavioral history from DB (last 20 windows) ---
        cur.execute(
            """
            SELECT r.event_timestamp, r.feature_vector
            FROM security.risk_scores_new r
            WHERE r.user_id = %s
            ORDER BY r.event_timestamp DESC
            LIMIT 20
            """,
            (data.user_id,),
        )
        history_rows = cur.fetchall()

        logon_counts = []
        device_counts = []
        past_logins = []
        for row in reversed(history_rows):  # oldest first
            fv = row["feature_vector"]
            if isinstance(fv, str):
                fv = json.loads(fv)
            # Reconstruct logon/device counts from feature vector
            logon_counts.append(max(1, int(round(fv.get("logon_deviation", 0) + 2))))
            device_counts.append(max(1, int(round(fv.get("device_deviation", 0) + 1))))
            past_logins.append(str(row["event_timestamp"]))

        user_history_dict = {
            "logon_counts": logon_counts,
            "unique_pcs_history": device_counts,
            "past_logins": past_logins,
            "current_logon_count": data.logons,
            "current_unique_pcs": data.devices,
            "current_logoff_count": 0,
        }

        # --- Feature engineering ---
        event_payload = {"timestamp": data.timestamp, "logons": data.logons, "devices": data.devices}
        raw_features = compute_features(event_payload, user_history_dict)
        features = {k: (v if v is not None else 0) for k, v in raw_features.items()}
        features["night_activity_flag"] = bool(features.get("night_activity_flag", False))

        # --- ML inference ---
        raw_model_flag, anomaly_score = predict(features)
        risk_value = anomaly_score_to_risk(anomaly_score)
        anomaly_flag = risk_value >= ANOMALY_FLAG_THRESHOLD
        risk_level = resolve_risk_level(risk_value)
        is_high_risk = risk_value >= RISK_THRESHOLD

        # --- Persist login event ---
        cur.execute(
            """
            INSERT INTO events.login_events
            (user_id, event_timestamp, login_status, ip_address, device_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (data.user_id, data.timestamp, "SUCCESS", data.ip_address, None),
        )

        # --- Persist feature vector ---
        cur.execute(
            """
            DELETE FROM features.user_behavior_features
            WHERE user_id = %s AND window_start = %s
            """,
            (data.user_id, data.timestamp),
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
                data.user_id, data.timestamp,
                features["z_logon"], features["z_pcs"],
                features["logon_deviation"], features["device_deviation"],
                features["device_ratio"], features["burst_score"],
                features["hour_deviation"], features["session_gap"],
                features["logon_logoff_ratio"], features["night_activity_flag"],
            ),
        )

        # --- Persist risk score ---
        cur.execute(
            """
            INSERT INTO security.risk_scores_new (
                user_id, anomaly_score, anomaly_flag, risk_score, risk_level,
                alert_flag, event_timestamp, model_version_id, feature_vector, window_start
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data.user_id, float(anomaly_score), bool(anomaly_flag),
                risk_value, risk_level, is_high_risk, data.timestamp,
                "if_v1_standard_scaler", json.dumps(features), data.timestamp,
            ),
        )

        # --- Auto-raise alert if high risk ---
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
                (data.user_id, data.user_id),
            )
            created_alert = cur.rowcount > 0

        conn.commit()

        # --- Fetch user metadata for the SSE payload ---
        cur.execute(
            """
            SELECT u.full_name, u.employee_id, d.department_name, r.role_name
            FROM core.users u
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles r ON r.role_id = u.role_id
            WHERE u.user_id = %s
            """,
            (data.user_id,),
        )
        user_meta = cur.fetchone() or {}

        result = {
            "type": "scored_event",
            "user_id": data.user_id,
            "full_name": user_meta.get("full_name", "Unknown"),
            "employee_id": user_meta.get("employee_id", ""),
            "department": user_meta.get("department_name", ""),
            "role": user_meta.get("role_name", ""),
            "timestamp": data.timestamp,
            "source": data.source,
            "logons": data.logons,
            "devices": data.devices,
            "ip_address": data.ip_address,
            "anomaly_flag": bool(anomaly_flag),
            "anomaly_score": float(anomaly_score),
            "risk_score": risk_value,
            "risk_level": risk_level,
            "alert_created": created_alert,
        }

        # --- Publish to SSE bus (non-blocking) ---
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(stream_engine.publish(result), loop)
        except Exception:
            pass  # Never let SSE failure block the HTTP response

        return result

    except HTTPException:
        if "conn" in locals():
            conn.rollback()
        raise
    except Exception as exc:
        if "conn" in locals():
            conn.rollback()
        logger.error("Stream ingest failed: %s", exc)
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/stream/live")
async def stream_live(token: Optional[str] = Query(default=None)):
    """
    Server-Sent Events endpoint.  The browser connects once and receives
    a continuous stream of scored events as they are ingested.

    Auth is via ?token=<bearer_token> query param because the browser
    EventSource API does not support custom headers.
    """
    # Validate token (same session store as the rest of the API)
    if token:
        try:
            conn, cur = get_cursor()
            cur.execute(
                """
                SELECT s.is_active FROM security.admin_sessions s
                WHERE s.session_token = %s AND s.is_active = TRUE
                  AND s.expires_at > CURRENT_TIMESTAMP
                LIMIT 1
                """,
                (token,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=401, detail="Invalid or expired token")
        except HTTPException:
            raise
        except Exception:
            pass  # Fail open during dev — tighten in production
        finally:
            if "cur" in locals():
                cur.close()
            if "conn" in locals():
                conn.close()

    # On connect, replay last 20 scored events from DB so the page has
    # immediate context rather than starting empty
    seed_events: list[dict] = []
    try:
        conn2, cur2 = get_cursor()
        cur2.execute(
            """
            SELECT
                r.user_id, r.risk_score, r.anomaly_flag, r.risk_level,
                r.anomaly_score, r.event_timestamp,
                u.full_name, u.employee_id,
                d.department_name, ro.role_name
            FROM security.risk_scores_new r
            JOIN core.users u ON u.user_id = r.user_id
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles ro ON ro.role_id = u.role_id
            ORDER BY r.event_timestamp DESC
            LIMIT 20
            """
        )
        for row in reversed(cur2.fetchall()):
            seed_events.append({
                "type": "seed_event",
                "user_id": str(row["user_id"]),
                "full_name": row["full_name"],
                "employee_id": row["employee_id"],
                "department": row["department_name"] or "",
                "role": row["role_name"] or "",
                "timestamp": str(row["event_timestamp"]),
                "risk_score": float(row["risk_score"] or 0),
                "anomaly_flag": bool(row["anomaly_flag"]),
                "risk_level": row["risk_level"] or "LOW",
                "anomaly_score": float(row["anomaly_score"] or 0),
                "source": "history",
            })
    except Exception:
        pass
    finally:
        if "cur2" in locals():
            cur2.close()
        if "conn2" in locals():
            conn2.close()

    async def event_generator() -> AsyncGenerator[str, None]:
        # First yield historical seed events so the UI isn't blank
        import json as _json
        for evt in seed_events:
            yield f"data: {_json.dumps(evt, default=str)}\n\n"
        # Then stream live events
        async for chunk in stream_engine.subscribe():
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/stream/status")
def stream_status():
    """Returns the current state of the replay engine and SSE bus."""
    return stream_engine.get_status()


@router.post("/stream/scenario")
def set_scenario(
    body: ScenarioRequest,
    authorization: Optional[str] = Header(default=None),
):
    """
    Set the active anomaly scenario for the live_replay.py demo engine.
    The replay engine polls this endpoint to determine which anomaly
    patterns to inject.
    """
    valid = {"normal", "burst_alert", "night_intrusion", "device_spread"}
    if body.scenario not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario. Must be one of: {sorted(valid)}",
        )
    stream_engine.set_scenario(body.scenario)
    return {"scenario": body.scenario, "message": "Scenario updated"}
