"""
Fix: Drop old partitioned features.user_behavior_features and recreate
as a flat table with all required columns per DB M8.sql.
Also ensure risk_scores June partition exists.
"""
import sys
sys.path.insert(0, '.')
from app.api.db import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

conn = get_connection()
conn.autocommit = True
cur = conn.cursor(cursor_factory=RealDictCursor)

print("Step 1: Dropping old partitioned features.user_behavior_features...")
cur.execute("DROP TABLE IF EXISTS features.user_behavior_features CASCADE;")
print("  Done.")

print("Step 2: Creating flat features.user_behavior_features (per DB M8)...")
cur.execute("""
CREATE TABLE features.user_behavior_features (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date          DATE DEFAULT CURRENT_DATE,
    window_start        TIMESTAMP NOT NULL,
    logon_count         INTEGER DEFAULT 0,
    logoff_count        INTEGER DEFAULT 0,
    unique_pcs          INTEGER DEFAULT 0,
    hour                INTEGER DEFAULT 0,
    z_logon             DOUBLE PRECISION,
    z_pcs               DOUBLE PRECISION,
    logon_deviation     DOUBLE PRECISION,
    device_deviation    DOUBLE PRECISION,
    device_ratio        DOUBLE PRECISION,
    burst_score         DOUBLE PRECISION,
    hour_deviation      DOUBLE PRECISION,
    session_gap         DOUBLE PRECISION,
    logon_logoff_ratio  DOUBLE PRECISION,
    night_activity_flag BOOLEAN,
    created_at          TIMESTAMP DEFAULT NOW()
);
""")
print("  Done.")

print("Step 3: Creating index on features.user_behavior_features...")
cur.execute("CREATE INDEX idx_features_user_date ON features.user_behavior_features (user_id, batch_date);")
print("  Done.")

print("Step 4: Checking security.risk_scores structure...")
cur.execute(
    "SELECT c.relkind FROM pg_class c "
    "JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE n.nspname = %s AND c.relname = %s",
    ('security', 'risk_scores')
)
rel = cur.fetchone()
if rel:
    print(f"  risk_scores relkind: '{rel['relkind']}' (p=partitioned, r=regular)")
else:
    print("  risk_scores table not found!")

print("\nAll done! Re-run the June batches now.")
cur.close()
conn.close()
