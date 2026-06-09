"""
Fix: Drop old partitioned security.risk_scores and security.alerts,
recreate as flat tables with all required columns per DB M8.sql.
"""
import sys
sys.path.insert(0, '.')
from app.api.db import get_connection
from psycopg2.extras import RealDictCursor

conn = get_connection()
conn.autocommit = True
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check current schemas
for schema, table in [('security', 'risk_scores'), ('security', 'alerts')]:
    cur.execute(
        "SELECT c.relkind FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relname = %s",
        (schema, table)
    )
    rel = cur.fetchone()
    kind = rel['relkind'] if rel else 'missing'
    print(f"  {schema}.{table}: relkind='{kind}' (p=partitioned, r=regular, missing=not found)")

print("\nStep 1: Dropping old tables CASCADE...")
cur.execute("DROP TABLE IF EXISTS security.alerts CASCADE;")
cur.execute("DROP TABLE IF EXISTS security.risk_scores CASCADE;")
cur.execute("DROP TABLE IF EXISTS security.risk_scores_old CASCADE;")
print("  Done.")

print("Step 2: Recreating flat security.risk_scores (per DB M8)...")
cur.execute("""
CREATE TABLE security.risk_scores (
    score_id            BIGSERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date          DATE DEFAULT CURRENT_DATE,
    window_start        TIMESTAMP NOT NULL,
    shift               VARCHAR(10) DEFAULT 'Day',
    role_group          VARCHAR(50) DEFAULT 'general',
    cluster_id          INTEGER,
    hdbscan_label       INTEGER,
    is_noise            BOOLEAN DEFAULT FALSE,
    if_score            DOUBLE PRECISION,
    risk_score          DOUBLE PRECISION,
    risk_level          VARCHAR(20),
    anomaly_flag        BOOLEAN DEFAULT FALSE,
    alert_flag          BOOLEAN DEFAULT FALSE,
    feature_vector      JSONB,
    cluster_probability DOUBLE PRECISION DEFAULT 1.0,
    if_anomaly          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW()
);
""")
print("  Done.")

print("Step 3: Creating risk_scores indexes...")
cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_user_date ON security.risk_scores (user_id, batch_date);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_anomaly   ON security.risk_scores (anomaly_flag);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_batch     ON security.risk_scores (batch_date DESC);")
print("  Done.")

print("Step 4: Recreating flat security.alerts (per DB M8)...")
cur.execute("""
CREATE TABLE security.alerts (
    alert_id                BIGSERIAL PRIMARY KEY,
    user_id                 UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date              DATE DEFAULT CURRENT_DATE,
    anomaly_count           INTEGER DEFAULT 1,
    window_days             INTEGER DEFAULT 7,
    severity                VARCHAR(20) DEFAULT 'HIGH',
    status                  VARCHAR(20) DEFAULT 'OPEN',
    email_analysis_triggered BOOLEAN DEFAULT FALSE,
    risk_score_id           BIGINT,
    created_at              TIMESTAMP DEFAULT NOW()
);
""")
print("  Done.")

print("Step 5: Creating alerts indexes...")
cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user   ON security.alerts (user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON security.alerts (status);")
print("  Done.")

# Verify
print("\n=== Verification ===")
for schema, table in [('security', 'risk_scores'), ('security', 'alerts'), ('features', 'user_behavior_features')]:
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema, table)
    )
    cols = [r['column_name'] for r in cur.fetchall()]
    print(f"  {schema}.{table}: {cols}")

cur.close()
conn.close()
print("\nAll fixed! Ready to re-run June batches.")
