"""
BehaviorGuard-AI — Phase 2 DB Migration: Flatten Tables
=========================================================
Drops all partitioned/old tables and recreates them as simple flat tables
suited for the new batch processing pipeline.

Steps:
  1. Drop partitioned tables (risk_scores_new, risk_scores, user_behavior_features)
  2. Create flat security.risk_scores
  3. Create flat features.user_behavior_features
  4. Drop and recreate security.alerts (batch-oriented schema)

Run from the project root inside the backend venv:
    python notebooks/db_migration_flatten.py
"""

import psycopg2

# ─── Connection ──────────────────────────────────────────────────────────────

conn = psycopg2.connect(
    dbname="behavior_guard_ai",
    user="postgres",
    password="Bhuvan2005!",
    host="localhost",
    port="5433",
)
conn.autocommit = False
cur = conn.cursor()

print("=" * 70)
print("BehaviorGuard-AI — Phase 2 DB Migration: Flatten Tables")
print("=" * 70)

# ─── STEP 1 — Drop partitioned tables ────────────────────────────────────────
print("\nSTEP 1 — Dropping old partitioned / legacy tables ...")

drops = [
    "DROP TABLE IF EXISTS security.risk_scores_new CASCADE;",
    "DROP TABLE IF EXISTS security.risk_scores CASCADE;",
    "DROP TABLE IF EXISTS features.user_behavior_features CASCADE;",
]

for sql in drops:
    cur.execute(sql)
    print(f"  ✓ {sql.strip()}")

# ─── STEP 2 — Create flat security.risk_scores ───────────────────────────────
print("\nSTEP 2 — Creating security.risk_scores (flat) ...")

cur.execute("""
CREATE TABLE security.risk_scores (
    score_id           BIGSERIAL PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES core.users(user_id),
    batch_date         DATE NOT NULL,
    window_start       TIMESTAMP NOT NULL,
    shift              VARCHAR(10) NOT NULL,
    role_group         VARCHAR(50) NOT NULL,
    cluster_id         INTEGER,
    hdbscan_label      INTEGER,
    is_noise           BOOLEAN DEFAULT FALSE,
    if_score           DOUBLE PRECISION,
    risk_score         DOUBLE PRECISION,
    risk_level         VARCHAR(20),
    anomaly_flag       BOOLEAN DEFAULT FALSE,
    alert_flag         BOOLEAN DEFAULT FALSE,
    feature_vector     JSONB,
    created_at         TIMESTAMP DEFAULT NOW()
);
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_user_date ON security.risk_scores (user_id, batch_date);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_anomaly   ON security.risk_scores (anomaly_flag);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_batch     ON security.risk_scores (batch_date DESC);")
print("  ✓ security.risk_scores created with 3 indexes")

# ─── STEP 3 — Create flat features.user_behavior_features ────────────────────
print("\nSTEP 3 — Creating features.user_behavior_features (flat) ...")

cur.execute("""
CREATE TABLE features.user_behavior_features (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES core.users(user_id),
    batch_date         DATE NOT NULL,
    window_start       TIMESTAMP NOT NULL,
    logon_count        INTEGER,
    logoff_count       INTEGER,
    unique_pcs         INTEGER,
    hour               INTEGER,
    z_logon            DOUBLE PRECISION,
    z_pcs              DOUBLE PRECISION,
    logon_deviation    DOUBLE PRECISION,
    device_deviation   DOUBLE PRECISION,
    device_ratio       DOUBLE PRECISION,
    burst_score        DOUBLE PRECISION,
    hour_deviation     DOUBLE PRECISION,
    session_gap        DOUBLE PRECISION,
    logon_logoff_ratio DOUBLE PRECISION,
    night_activity_flag BOOLEAN,
    created_at         TIMESTAMP DEFAULT NOW()
);
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_features_user_date ON features.user_behavior_features (user_id, batch_date);")
print("  ✓ features.user_behavior_features created with 1 index")

# ─── STEP 4 — Drop old alerts table and recreate ─────────────────────────────
print("\nSTEP 4 — Dropping old security.alerts and recreating (batch schema) ...")

cur.execute("DROP TABLE IF EXISTS security.alerts CASCADE;")
print("  ✓ DROP TABLE IF EXISTS security.alerts CASCADE")

cur.execute("""
CREATE TABLE security.alerts (
    alert_id           BIGSERIAL PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES core.users(user_id),
    batch_date         DATE NOT NULL,
    anomaly_count      INTEGER NOT NULL,
    window_days        INTEGER NOT NULL,
    severity           VARCHAR(20) DEFAULT 'HIGH',
    status             VARCHAR(20) DEFAULT 'OPEN',
    email_analysis_triggered BOOLEAN DEFAULT FALSE,
    created_at         TIMESTAMP DEFAULT NOW()
);
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user   ON security.alerts (user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON security.alerts (status);")
print("  ✓ security.alerts recreated with 2 indexes")

# ─── COMMIT ───────────────────────────────────────────────────────────────────
conn.commit()
print("\n  ✅ All changes committed.")

# ─── VERIFICATION ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("VERIFICATION — Table existence and row counts")
print("=" * 70)

tables = [
    ("security",  "risk_scores"),
    ("features",  "user_behavior_features"),
    ("security",  "alerts"),
]

all_ok = True
for schema, table in tables:
    # Confirm table exists
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
        """,
        (schema, table),
    )
    exists = cur.fetchone()[0]

    if exists:
        cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
        count = cur.fetchone()[0]
        print(f"  ✓ {schema}.{table:<30} exists  |  rows: {count}")
    else:
        print(f"  ✗ {schema}.{table:<30} MISSING — migration may have failed!")
        all_ok = False

# Also confirm old partitioned tables are gone
print("\nConfirming old partitioned tables are dropped ...")
old_tables = [
    ("security", "risk_scores_new"),
]
for schema, table in old_tables:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
        """,
        (schema, table),
    )
    exists = cur.fetchone()[0]
    status = "STILL EXISTS (unexpected)" if exists else "gone (expected)"
    mark   = "✗" if exists else "✓"
    print(f"  {mark} {schema}.{table:<30} {status}")
    if exists:
        all_ok = False

print("\n" + "=" * 70)
if all_ok:
    print("Migration complete — all tables verified.")
else:
    print("WARNING: One or more checks failed. Review output above.")
print("=" * 70)

cur.close()
conn.close()
