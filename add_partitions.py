import psycopg2

conn = psycopg2.connect(
    dbname="behavior_guard_ai",
    user="postgres",
    password="password",
    host="localhost",
    port="5432"
)
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS features.user_behavior_features_2026_03
    PARTITION OF features.user_behavior_features
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

    CREATE TABLE IF NOT EXISTS security.risk_scores_2026_03
    PARTITION OF security.risk_scores_new
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
    """)
    print("Created March 2026 partition tables.")
except Exception as e:
    print("Error:", e)

cur.close()
conn.close()
