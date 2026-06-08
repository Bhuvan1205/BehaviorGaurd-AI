import logging
import hashlib
import os
import secrets
import shutil
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.api.db import get_cursor
from app.config import RISK_THRESHOLD

# ── In-process job store (survives for the lifetime of the server process) ────
# Structure: { job_id: { status, batch_date, file_path, summary, error, started_at, finished_at } }
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


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





def fetch_latest_open_alert(cur, user_id: str):
    cur.execute(
        """
        SELECT alert_id, user_id, batch_date, anomaly_count, window_days, severity, status, created_at, NULL AS risk_score_id
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
                    r.window_start AS latest_event_timestamp
                FROM security.risk_scores r
                ORDER BY r.user_id, r.window_start DESC
            ),
            risk_stats AS (
                SELECT
                    r.user_id,
                    AVG(r.risk_score) AS avg_risk,
                    COUNT(*) AS history_count,
                    SUM(CASE WHEN r.anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
                FROM security.risk_scores r
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
                    r.window_start AS latest_event_timestamp
                FROM security.risk_scores r
                WHERE r.user_id = %s
                ORDER BY r.user_id, r.window_start DESC
            ),
            latest_batch_stats AS (
                SELECT
                    r.user_id,
                    COALESCE((SUM(CASE WHEN r.anomaly_flag = TRUE THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0)::float) * 100, 0) AS latest_anomaly_rate,
                    COALESCE(SUM(CASE WHEN r.anomaly_flag = TRUE THEN 1 ELSE 0 END), 0) AS latest_anomaly_count,
                    COALESCE(COUNT(*), 0) AS latest_total_windows
                FROM security.risk_scores r
                WHERE r.user_id = %s
                  AND r.batch_date = (SELECT MAX(batch_date) FROM security.risk_scores WHERE user_id = %s)
                GROUP BY r.user_id
            ),
            risk_stats AS (
                SELECT
                    r.user_id,
                    AVG(r.risk_score) AS avg_risk,
                    COUNT(*) AS history_count,
                    SUM(CASE WHEN r.anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
                FROM security.risk_scores r
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
                COALESCE(al.open_alert_count, 0) AS open_alert_count,
                COALESCE(lbs.latest_anomaly_rate, 0) AS latest_anomaly_rate,
                COALESCE(lbs.latest_anomaly_count, 0) AS latest_anomaly_count,
                COALESCE(lbs.latest_total_windows, 0) AS latest_total_windows
            FROM core.users u
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles rl ON rl.role_id = u.role_id
            LEFT JOIN latest_risk lr ON lr.user_id = u.user_id
            LEFT JOIN latest_batch_stats lbs ON lbs.user_id = u.user_id
            LEFT JOIN risk_stats rs ON rs.user_id = u.user_id
            LEFT JOIN alert_stats al ON al.user_id = u.user_id
            WHERE u.user_id = %s
            LIMIT 1
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id),
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
                    (SELECT COALESCE(SUM(logon_count), 0) FROM features.user_behavior_features) AS login_events,
                    (SELECT COUNT(*) FROM security.alerts) AS alerts_total,
                    (SELECT COUNT(*) FROM security.alerts WHERE status = 'OPEN') AS alerts_open,
                    (SELECT COALESCE(AVG(risk_score), 0) FROM security.risk_scores) AS avg_risk,
                    (SELECT COUNT(*) FROM security.risk_scores WHERE risk_score >= %s) AS high_risk_windows
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
                FROM security.risk_scores
                WHERE batch_date = (SELECT MAX(batch_date) FROM security.risk_scores)
                GROUP BY 1
            ),
            user_risk AS (
                SELECT
                    u.user_id,
                    u.full_name,
                    u.employee_id,
                    d.department_name,
                    rl.role_name,
                    COALESCE((SUM(CASE WHEN r.anomaly_flag = TRUE THEN 1 ELSE 0 END)::float / NULLIF(COUNT(r.window_start), 0)::float) * 100, 0) AS anomaly_ratio,
                    COALESCE(SUM(CASE WHEN r.anomaly_flag = TRUE THEN 1 ELSE 0 END), 0) AS anomalous_windows,
                    COALESCE(COUNT(r.window_start), 0) AS total_windows,
                    COALESCE(AVG(r.risk_score), 0) AS avg_risk
                FROM core.users u
                LEFT JOIN core.departments d ON d.department_id = u.department_id
                LEFT JOIN core.roles rl ON rl.role_id = u.role_id
                LEFT JOIN security.risk_scores r ON r.user_id = u.user_id AND r.batch_date = (SELECT MAX(batch_date) FROM security.risk_scores)
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
                    ur.anomaly_ratio,
                    ur.anomalous_windows,
                    ur.total_windows,
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
                    anomaly_ratio,
                    anomalous_windows,
                    total_windows,
                    open_alert_count
                FROM user_rollup
                ORDER BY anomaly_ratio DESC, open_alert_count DESC, full_name
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
                    COALESCE(AVG(anomaly_ratio), 0) / 100.0 AS avg_risk,
                    COALESCE(SUM(open_alert_count), 0) AS open_alert_count
                FROM user_rollup
                GROUP BY department_name
                ORDER BY avg_risk DESC, open_alert_count DESC, department_name
                LIMIT 8
            ),
            weekly_trends AS (
                SELECT
                    batch_date::text AS batch_date,
                    COUNT(*) AS total_windows,
                    SUM(CASE WHEN anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count,
                    COALESCE((SUM(CASE WHEN anomaly_flag = TRUE THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0)::float) * 100, 0) AS anomaly_rate,
                    COALESCE(AVG(risk_score), 0) AS avg_risk_score
                FROM security.risk_scores
                GROUP BY batch_date
                ORDER BY batch_date ASC
            )
            SELECT json_build_object(
                'totals', (SELECT row_to_json(org_metrics) FROM org_metrics),
                'risk_distribution', (SELECT COALESCE(json_agg(risk_bands ORDER BY band), '[]'::json) FROM risk_bands),
                'top_users', (SELECT COALESCE(json_agg(top_users), '[]'::json) FROM top_users),
                'recent_alerts', (SELECT COALESCE(json_agg(recent_alerts), '[]'::json) FROM recent_alerts),
                'department_rollup', (SELECT COALESCE(json_agg(dept_rollup), '[]'::json) FROM dept_rollup),
                'weekly_trends', (SELECT COALESCE(json_agg(weekly_trends), '[]'::json) FROM weekly_trends)
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
            SELECT r.score_id, r.if_score AS anomaly_score, r.anomaly_flag, r.risk_score, r.risk_level,
                   r.alert_flag, r.window_start AS event_timestamp, NULL AS model_version_id, r.window_start, r.created_at,
                   r.feature_vector, COALESCE(f.logon_count, 0) AS logon_count,
                   COALESCE(f.unique_pcs, 0) AS device_count, r.cluster_probability, r.if_anomaly
            FROM security.risk_scores r
            LEFT JOIN features.user_behavior_features f
              ON f.user_id = r.user_id AND f.window_start = r.window_start
            WHERE r.user_id = %s
            ORDER BY r.window_start DESC
            LIMIT 100
            """,
            (user_id,),
        )
        windows = [dict(r) for r in cur.fetchall()]

        # Query weekly trends for this user
        cur.execute(
            """
            SELECT
                batch_date::text AS batch_date,
                COUNT(*) AS total_windows,
                SUM(CASE WHEN anomaly_flag = TRUE THEN 1 ELSE 0 END) AS anomaly_count,
                COALESCE((SUM(CASE WHEN anomaly_flag = TRUE THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0)::float) * 100, 0) AS anomaly_rate
            FROM security.risk_scores
            WHERE user_id = %s
            GROUP BY batch_date
            ORDER BY batch_date ASC
            """,
            (user_id,),
        )
        weekly_trends = [dict(r) for r in cur.fetchall()]

        return {
            "windows": windows,
            "weekly_trends": weekly_trends
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/alerts")
def get_alerts(
    user_id: Optional[str] = Query(default=None),
    batch_date: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    latest_only: bool = Query(default=True),
    authorization: Optional[str] = Header(default=None)
):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        
        # Build SQL query dynamically
        query = """
            SELECT a.alert_id, a.user_id, a.batch_date::text, a.anomaly_count, a.window_days, a.severity, a.status, a.created_at,
                   u.full_name, u.employee_id, d.department_name AS department, rl.role_name AS role
            FROM security.alerts a
            JOIN core.users u ON u.user_id = a.user_id
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles rl ON rl.role_id = u.role_id
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND a.user_id = %s::uuid"
            params.append(user_id)
        else:
            # When user_id is not specified, we might want to filter by batch_date
            resolved_batch_date = batch_date
            if not resolved_batch_date and latest_only:
                cur.execute("SELECT MAX(batch_date) AS max_date FROM security.alerts")
                max_row = cur.fetchone()
                if max_row and max_row["max_date"]:
                    resolved_batch_date = str(max_row["max_date"])
            
            if resolved_batch_date:
                query += " AND a.batch_date = %s"
                params.append(resolved_batch_date)
                
        if status:
            query += " AND a.status = %s"
            params.append(status)
            
        query += " ORDER BY a.created_at DESC LIMIT 200"
        
        cur.execute(query, tuple(params))
        return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


class UpdateAlertRequest(BaseModel):
    status: str


@router.patch("/alerts/{alert_id}")
def update_alert(
    alert_id: int,
    data: UpdateAlertRequest,
    authorization: Optional[str] = Header(default=None)
):
    if data.status not in ["OPEN", "RESOLVED"]:
        raise HTTPException(status_code=400, detail="Status must be OPEN or RESOLVED")
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        cur.execute(
            """
            UPDATE security.alerts
            SET status = %s
            WHERE alert_id = %s
            RETURNING alert_id, status
            """,
            (data.status, alert_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        conn.commit()
        return dict(row)
    except Exception as exc:
        if "conn" in locals():
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


@router.get("/anomalies")
def get_all_anomalies(
    user_id: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None)
):
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
        
        query = """
            SELECT r.score_id, r.user_id, r.batch_date::text, r.window_start::text AS timestamp, 
                   r.shift, r.role_group, r.hdbscan_label, r.is_noise, r.if_score AS anomaly_score, 
                   r.risk_score, r.risk_level, r.anomaly_flag, r.alert_flag, r.feature_vector,
                   r.cluster_probability, r.if_anomaly,
                   u.full_name, u.employee_id, d.department_name AS department, rl.role_name AS role
            FROM security.risk_scores r
            JOIN core.users u ON u.user_id = r.user_id
            LEFT JOIN core.departments d ON d.department_id = u.department_id
            LEFT JOIN core.roles rl ON rl.role_id = u.role_id
            WHERE r.anomaly_flag = TRUE
        """
        params = []
        if user_id:
            query += " AND r.user_id = %s::uuid"
            params.append(user_id)
            
        query += " ORDER BY r.window_start DESC LIMIT 200"
        
        cur.execute(query, tuple(params))
        return [dict(row) for row in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


# ---------------------------------------------------------------------------
# PIPELINE ENDPOINTS
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "daily_logs",
)


def _run_pipeline_job(job_id: str, file_path: str, batch_date: str) -> None:
    """
    Executed in a background thread.
    Updates the job store on completion or failure.
    """
    from app.services.batch_pipeline import run_batch_pipeline  # lazy import avoids circular

    with _jobs_lock:
        _jobs[job_id]["status"] = "running"

    try:
        summary = run_batch_pipeline(file_path, batch_date)
        with _jobs_lock:
            _jobs[job_id].update({
                "status":      "complete",
                "summary":     summary,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.info("Pipeline job %s finished: %s", job_id, summary)

    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id].update({
                "status":      "failed",
                "error":       str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.exception("Pipeline job %s failed", job_id)


@router.post("/pipeline/upload-log")
async def upload_log(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV log file (columns: user_id, timestamp, logon_count, logoff_count, unique_pcs)"),
    batch_date: Optional[str] = Query(
        default=None,
        description="Date for this batch (YYYY-MM-DD). Defaults to today's UTC date.",
    ),
    authorization: Optional[str] = Header(default=None),
):
    """
    Upload a daily log CSV and trigger the batch ML pipeline.

    Returns immediately with a **job_id** — the pipeline runs in the
    background.  Poll ``GET /pipeline/status/{job_id}`` for results.

    The file is saved to ``data/daily_logs/{batch_date}_log.csv``
    before the pipeline is started.
    """
    # Auth
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()

    # Resolve batch_date
    if not batch_date:
        batch_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        # Validate format
        try:
            datetime.strptime(batch_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"batch_date must be YYYY-MM-DD, got: {batch_date!r}",
            )

    # Validate file extension
    filename = file.filename or "upload.csv"
    ext = os.path.splitext(filename.lower())[1]
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a .csv, .xlsx, or .xls"
        )

    # Save file
    os.makedirs(_LOG_DIR, exist_ok=True)
    dest_path = os.path.join(_LOG_DIR, f"{batch_date}_log{ext}")
    try:
        with open(dest_path, "wb") as fh:
            shutil.copyfileobj(file.file, fh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}") from exc
    finally:
        await file.close()

    # Register job
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id":     job_id,
            "status":     "queued",
            "batch_date": batch_date,
            "file_path":  dest_path,
            "summary":    None,
            "error":      None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }

    # Launch background task
    background_tasks.add_task(_run_pipeline_job, job_id, dest_path, batch_date)

    logger.info(
        "Pipeline job %s queued | batch_date=%s | file=%s",
        job_id, batch_date, dest_path,
    )

    return {
        "job_id":      job_id,
        "status":      "queued",
        "batch_date":  batch_date,
        "file_saved":  dest_path,
        "message":     "Pipeline started. Poll /pipeline/status/{job_id} for results.",
    }


@router.get("/pipeline/status/{job_id}")
def pipeline_status(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """
    Return the current status of a pipeline job.

    Possible status values:
      - ``queued``   — job is waiting to start
      - ``running``  — pipeline is executing
      - ``complete`` — finished successfully; ``summary`` field contains results
      - ``failed``   — pipeline raised an exception; ``error`` field contains message
    """
    # Auth
    try:
        conn, cur = get_cursor()
        get_current_admin(cur, authorization)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()

    with _jobs_lock:
        job = _jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id!r} not found. It may have expired or never existed.",
        )

    return job
