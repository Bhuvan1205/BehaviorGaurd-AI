"""
BehaviorGuard-AI — Batch Processing Pipeline
=============================================
Processes a single week's log file through the full ML pipeline:

  Step 1  — Load & validate log CSV or Excel, map employee_id → UUID
  Step 2  — Feature engineering (feature_engine.py)
  Step 3  — Run V6 clustering and anomaly scoring (inference.py)
  Step 4  — Bulk insert risk scores & feature vectors to security.risk_scores
  Step 5  — Alert threshold check (N anomalous weeks in Y-day window)
  Step 6  — Return summary dict
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
import pandas as pd

from app.api.db import get_cursor
from app.services.feature_engine import compute_features, write_features_to_db, IF_FEATURES
from app.services.inference import run_inference

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# ── Constants ─────────────────────────────────────────────────────────────────
ALERT_ANOMALY_DAYS  = 3    # N anomalous weeks/runs required
ALERT_WINDOW_DAYS   = 60   # Y-day lookback window (extended for weekly batching)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Load & validate log CSV or Excel
# ─────────────────────────────────────────────────────────────────────────────

def _step1_load_log(log_file_path: str, cur) -> pd.DataFrame:
    logger.info("Step 1 — Loading log file: %s", log_file_path)

    # Detect extension and parse accordingly
    ext = os.path.splitext(log_file_path.lower())[1]
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(log_file_path)
    else:
        df = pd.read_csv(log_file_path)

    original_count = len(df)

    required_cols = {"user_id", "timestamp", "logon_count", "logoff_count", "unique_pcs"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Log file missing required columns: {missing}")

    # Map alphanumeric employee_id → UUID user_id
    employee_ids = df["user_id"].dropna().unique().tolist()
    placeholders = ",".join(["%s"] * len(employee_ids))
    cur.execute(
        f"SELECT user_id, employee_id FROM core.users WHERE employee_id = ANY(ARRAY[{placeholders}])",
        employee_ids,
    )
    id_map = {row["employee_id"]: str(row["user_id"]) for row in cur.fetchall()}

    df["uuid"] = df["user_id"].map(id_map)
    dropped = df["uuid"].isna().sum()
    df = df.dropna(subset=["uuid"]).copy()
    df["user_id"] = df["uuid"]
    df = df.drop(columns=["uuid"])

    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = df["timestamp"].isna().sum()
    df = df.dropna(subset=["timestamp"])

    logger.info(
        "Step 1 — Loaded %d rows | dropped %d unmapped users | dropped %d bad timestamps | kept %d",
        original_count, dropped, bad_ts, len(df),
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Bulk insert risk scores with V6 columns
# ─────────────────────────────────────────────────────────────────────────────

def _write_risk_scores(df: pd.DataFrame, batch_date: str, conn, cur) -> None:
    logger.info("Step 4 — Writing %d risk scores to DB ...", len(df))

    records = []
    for _, row in df.iterrows():
        fv = {f: (bool(row[f]) if f == "night_activity_flag" else float(row.get(f, 0)))
              for f in IF_FEATURES}
        records.append((
            str(row["user_id"]),
            batch_date,
            row["window_start"].isoformat() if hasattr(row["window_start"], "isoformat") else str(row["window_start"]),
            str(row["shift"]),
            str(row["role_group"]),
            int(row["hdbscan_label"]), # cluster_id backward compatibility
            int(row["hdbscan_label"]),
            bool(row["is_noise"]),
            float(row["if_score"]),
            float(row["risk_score"]),
            str(row["risk_level"]),
            bool(row["anomaly_flag"]),
            False,                          # alert_flag — set in step 5
            json.dumps(fv),
            float(row["cluster_probability"]),
            bool(row["if_anomaly"]),
        ))

    from psycopg2.extras import execute_values
    execute_values(
        cur,
        """
        INSERT INTO security.risk_scores
          (user_id, batch_date, window_start, shift, role_group,
           cluster_id, hdbscan_label, is_noise, if_score, risk_score,
           risk_level, anomaly_flag, alert_flag, feature_vector,
           cluster_probability, if_anomaly)
        VALUES %s
        """,
        records,
        page_size=2000
    )
    logger.info("Step 4 — Inserted %d rows into security.risk_scores", len(records))


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Alert threshold check
# ─────────────────────────────────────────────────────────────────────────────

def _alert_check(df: pd.DataFrame, batch_date: str, conn, cur) -> int:
    logger.info("Step 5 — Alert threshold check ...")

    alerts_generated = 0
    cutoff_date = (
        datetime.strptime(batch_date, "%Y-%m-%d") - timedelta(days=ALERT_WINDOW_DAYS)
    ).strftime("%Y-%m-%d")

    user_ids = df["user_id"].unique().tolist()

    # Query distinct weeks with >=1 anomaly in the rolling window for all users in one batch
    anomaly_days_map = {}
    if user_ids:
        cur.execute(
            """
            SELECT user_id::text, COUNT(DISTINCT batch_date) AS anomaly_days
            FROM security.risk_scores
            WHERE user_id = ANY(%s::uuid[])
              AND batch_date >= %s
              AND anomaly_flag = TRUE
            GROUP BY user_id
            """,
            (user_ids, cutoff_date),
        )
        rows = cur.fetchall()
        anomaly_days_map = {row["user_id"]: int(row["anomaly_days"]) for row in rows}

    for user_id in user_ids:
        anomaly_days = anomaly_days_map.get(user_id, 0)

        if anomaly_days >= ALERT_ANOMALY_DAYS:
            # Flip alert_flag on all records for this user/batch_date
            cur.execute(
                """
                UPDATE security.risk_scores
                SET alert_flag = TRUE
                WHERE user_id = %s::uuid AND batch_date = %s
                """,
                (user_id, batch_date),
            )

            # Insert alert only if no OPEN alert already exists
            cur.execute(
                """
                INSERT INTO security.alerts
                  (user_id, batch_date, anomaly_count, window_days, severity, status)
                SELECT %s::uuid, %s, %s, %s, 'HIGH', 'OPEN'
                WHERE NOT EXISTS (
                    SELECT 1 FROM security.alerts
                    WHERE user_id = %s::uuid AND status = 'OPEN'
                )
                """,
                (user_id, batch_date, anomaly_days, ALERT_WINDOW_DAYS, user_id),
            )
            if cur.rowcount > 0:
                alerts_generated += 1
                logger.info(
                    "  ALERT raised for user_id=%s | anomaly_weeks=%d",
                    user_id, anomaly_days,
                )

    logger.info("Step 5 — %d new alerts generated", alerts_generated)
    return alerts_generated


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_batch_pipeline(log_file_path: str, batch_date: str) -> dict:
    """
    Execute the full batch pipeline for a weekly log file.

    Parameters
    ----------
    log_file_path : str
        Absolute or relative path to the CSV/Excel log file.
    batch_date : str
        ISO date string, e.g. "2026-06-05". Used as the partition key.

    Returns
    -------
    dict
        Summary of the run.
    """
    t_start = time.perf_counter()
    logger.info("=" * 70)
    logger.info("Weekly Batch pipeline starting  |  batch_date=%s  |  file=%s",
                batch_date, log_file_path)
    logger.info("=" * 70)

    conn, cur = get_cursor()
    try:
        # Step 1: Load Log Data
        df = _step1_load_log(log_file_path, cur)
        if df.empty:
            logger.warning("No valid rows after Step 1 — aborting pipeline.")
            return {
                "batch_date": batch_date,
                "total_records": 0,
                "total_users": 0,
                "anomalies_detected": 0,
                "alerts_generated": 0,
                "noise_points": 0,
                "processing_time_seconds": round(time.perf_counter() - t_start, 2),
            }

        # Step 2: Feature Engineering
        df_features = compute_features(df, batch_date, cur)

        # Save features to DB
        write_features_to_db(df_features, batch_date, cur)

        # Step 3: Run ML Inference (V6 Clustering & Anomaly detection)
        df_scored = run_inference(df_features, cur)

        # Step 4: Write Risk Scores to DB
        _write_risk_scores(df_scored, batch_date, conn, cur)

        # Step 5: Check Alert Thresholds
        alerts_generated = _alert_check(df_scored, batch_date, conn, cur)

        # Commit transaction
        conn.commit()

        # Step 6: Run RAG-based email pipeline on top 5% anomalous users
        email_summary = {}
        try:
            from app.services.email_pipeline import run_email_pipeline_for_batch
            email_summary = run_email_pipeline_for_batch(batch_date, df_scored)
            logger.info("Email pipeline executed: %s", email_summary)
        except Exception as e:
            logger.error("Failed to run email RAG pipeline in batch: %s", e)

        elapsed = round(time.perf_counter() - t_start, 2)
        summary = {
            "batch_date":               batch_date,
            "total_records":            int(len(df_scored)),
            "total_users":              int(df_scored["user_id"].nunique()),
            "anomalies_detected":       int(df_scored["anomaly_flag"].sum()),
            "alerts_generated":         alerts_generated,
            "noise_points":             int(df_scored["is_noise"].sum()),
            "processing_time_seconds":  elapsed,
            "email_audits_status":      email_summary.get("status", "failed"),
            "email_audited_count":      email_summary.get("analyzed_users_count", 0),
        }
        logger.info("=" * 70)
        logger.info("Weekly Pipeline complete: %s", summary)
        logger.info("=" * 70)
        return summary

    except Exception:
        conn.rollback()
        logger.exception("Batch pipeline failed — rolled back.")
        raise
    finally:
        cur.close()
        conn.close()
