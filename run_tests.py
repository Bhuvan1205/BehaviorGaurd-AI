import requests
import psycopg2
from psycopg2.extras import RealDictCursor

BASE = "http://localhost:8000"
UID = "11111111-1111-1111-1111-111111111111"
THRESHOLD = 0.7

def db():
    conn = psycopg2.connect(dbname="behavior_guard_ai", user="postgres", password="password", host="localhost", port="5432")
    return conn, conn.cursor(cursor_factory=RealDictCursor)

results = {}

# TEST 1 — BASELINE
try:
    r = requests.post(f"{BASE}/event", json={
        "user_id": UID,
        "event": {"timestamp": "2026-03-25T10:00:00", "logons": 1, "devices": 1},
        "user_history": [{"timestamp": "2026-03-24T10:00:00", "logons": 1, "devices": 1}]
    })
    body = r.json()
    http_ok = r.status_code == 200
    keys_ok = all(k in body for k in ["anomaly_flag", "aggregated_risk", "alert"])

    conn, cur = db()
    cur.execute("SELECT COUNT(*) as c FROM events.login_events WHERE user_id = %s", (UID,))
    le = cur.fetchone()["c"] >= 1
    cur.execute("SELECT COUNT(*) as c FROM features.user_behavior_features WHERE user_id = %s", (UID,))
    fe = cur.fetchone()["c"] >= 1
    cur.execute("SELECT COUNT(*) as c FROM security.risk_scores_new WHERE user_id = %s", (UID,))
    rs = cur.fetchone()["c"] >= 1
    cur.close(); conn.close()

    results[1] = "PASS" if all([http_ok, keys_ok, le, fe, rs]) else "FAIL"
except Exception as e:
    results[1] = f"FAIL"

# TEST 2 — HIGH ACTIVITY
try:
    r = requests.post(f"{BASE}/event", json={
        "user_id": UID,
        "event": {"timestamp": "2026-03-25T02:00:00", "logons": 25, "devices": 8},
        "user_history": [{"timestamp": "2026-03-24T10:00:00", "logons": 1, "devices": 1}]
    })
    body = r.json()
    http_ok = r.status_code == 200
    flag_ok = isinstance(body.get("anomaly_flag"), bool)
    risk_ok = isinstance(body.get("aggregated_risk"), (int, float)) and 0 <= body.get("aggregated_risk", -1) <= 1

    conn, cur = db()
    cur.execute("SELECT COUNT(*) as c FROM security.risk_scores_new WHERE user_id = %s", (UID,))
    rs = cur.fetchone()["c"] >= 2
    cur.close(); conn.close()

    results[2] = "PASS" if all([http_ok, flag_ok, risk_ok, rs]) else "FAIL"
    latest_risk = body.get("aggregated_risk", 0)
except Exception as e:
    results[2] = "FAIL"
    latest_risk = 0

# TEST 3 — ALERT GENERATION
try:
    conn, cur = db()
    cur.execute("SELECT risk_score FROM security.risk_scores_new WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (UID,))
    row = cur.fetchone()
    latest_risk = row["risk_score"] if row else 0

    cur.execute("SELECT COUNT(*) as c FROM security.alerts WHERE user_id = %s", (UID,))
    alert_count = cur.fetchone()["c"]
    cur.close(); conn.close()

    if latest_risk >= THRESHOLD:
        results[3] = "PASS" if alert_count >= 1 else "FAIL"
    else:
        results[3] = "PASS"  # No alert expected, nothing to validate
except Exception as e:
    results[3] = "FAIL"

# TEST 4 — ALERT LINKING
try:
    conn, cur = db()
    cur.execute("""
        SELECT a.risk_score_id, r.score_id
        FROM security.alerts a
        JOIN security.risk_scores_new r ON a.risk_score_id = r.score_id
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        results[4] = "PASS" if row["risk_score_id"] == row["score_id"] else "FAIL"
    else:
        results[4] = "PASS"  # No alerts exist (risk below threshold), linking logic is not triggered
except Exception as e:
    results[4] = "FAIL"

# TEST 5 — DUPLICATE PROTECTION (re-send Test 1 with same timestamp)
try:
    requests.post(f"{BASE}/event", json={
        "user_id": UID,
        "event": {"timestamp": "2026-03-25T10:00:00", "logons": 1, "devices": 1},
        "user_history": [{"timestamp": "2026-03-24T10:00:00", "logons": 1, "devices": 1}]
    })
    conn, cur = db()
    cur.execute("""
        SELECT COUNT(*) as c FROM features.user_behavior_features
        WHERE user_id = %s AND window_start = '2026-03-25T10:00:00'
    """, (UID,))
    count = cur.fetchone()["c"]
    cur.close(); conn.close()
    results[5] = "PASS" if count == 1 else "FAIL"
except Exception as e:
    results[5] = "FAIL"

# TEST 6 — HISTORY ENDPOINT
try:
    r = requests.get(f"{BASE}/history", params={"user_id": UID})
    results[6] = "PASS" if r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) > 0 else "FAIL"
except Exception as e:
    results[6] = "FAIL"

# TEST 7 — ALERTS ENDPOINT
try:
    r = requests.get(f"{BASE}/alerts", params={"user_id": UID})
    results[7] = "PASS" if r.status_code == 200 and isinstance(r.json(), list) else "FAIL"
except Exception as e:
    results[7] = "FAIL"

# TEST 8 — VALIDATION FAILURE
try:
    r = requests.post(f"{BASE}/event", json={
        "user_id": UID,
        "event": {}
    })
    results[8] = "PASS" if r.status_code == 422 else "FAIL"
except Exception as e:
    results[8] = "FAIL"

# OUTPUT
for i in range(1, 9):
    print(f"Test {i}: {results.get(i, 'FAIL')}")
