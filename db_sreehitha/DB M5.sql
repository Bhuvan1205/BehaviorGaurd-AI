-- =====================================================
-- BehaviorGuard-AI
-- Milestone 5: ML Feature Store & Prediction Storage
-- =====================================================

-- =====================================================
-- 1. Feature Store Table (Hourly Behavioral Features)
-- =====================================================

CREATE TABLE features.user_behavior_features (
    id BIGSERIAL,
    user_id UUID REFERENCES core.users(user_id),
    window_start TIMESTAMP NOT NULL,

    -- Behavioral Features (ML Input)
    z_logon FLOAT,
    z_pcs FLOAT,
    logon_deviation FLOAT,
    device_deviation FLOAT,
    device_ratio FLOAT,
    burst_score FLOAT,
    hour_deviation FLOAT,
    session_gap FLOAT,
    logon_logoff_ratio FLOAT,
    night_activity_flag BOOLEAN,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id, window_start)
) PARTITION BY RANGE (window_start);


-- =====================================================
-- 2. Example Monthly Partition (Create Monthly)
-- =====================================================

CREATE TABLE features.user_behavior_features_2026_01
PARTITION OF features.user_behavior_features
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE features.user_behavior_features_2026_02
PARTITION OF features.user_behavior_features
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');


-- =====================================================
-- 3. Indexes for Feature Table
-- =====================================================

CREATE INDEX idx_behavior_user_time
ON features.user_behavior_features(user_id, window_start DESC);

CREATE INDEX idx_behavior_time
ON features.user_behavior_features(window_start DESC);


-- =====================================================
-- 4. Modify Risk Scores Table (Add Window + Model Version)
-- =====================================================

ALTER TABLE security.risk_scores
ADD COLUMN IF NOT EXISTS window_start TIMESTAMP;

ALTER TABLE security.risk_scores
ADD COLUMN IF NOT EXISTS model_version_id UUID
REFERENCES ml.model_versions(version_id);


-- =====================================================
-- 5. Convert Risk Scores Table to Partitioned Table
-- =====================================================

-- Create new partitioned table structure
CREATE TABLE security.risk_scores_new (
    score_id BIGSERIAL,
    user_id UUID REFERENCES core.users(user_id),
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    window_start TIMESTAMP NOT NULL,
    risk_score FLOAT,
    anomaly_flag BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (score_id, window_start)
) PARTITION BY RANGE (window_start);


-- Example partitions
CREATE TABLE security.risk_scores_2026_01
PARTITION OF security.risk_scores_new
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE security.risk_scores_2026_02
PARTITION OF security.risk_scores_new
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');


-- =====================================================
-- 6. Indexes for Risk Scores
-- =====================================================

CREATE INDEX idx_risk_anomaly
ON security.risk_scores_new(anomaly_flag);

CREATE INDEX idx_risk_score
ON security.risk_scores_new(risk_score DESC);


-- =====================================================
-- 7. Retention Policy Tables (Optional Logging)
-- =====================================================

CREATE TABLE IF NOT EXISTS audit.data_retention_log (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100),
    deleted_records INTEGER,
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================
-- Schema Updates for ML Traceability
-- =====================================================

-- 1. Add anomaly_score (raw ML model output)
ALTER TABLE security.risk_scores_new
ADD COLUMN IF NOT EXISTS anomaly_score DOUBLE PRECISION;

-- 2. Add event_timestamp (actual event time vs window time)
ALTER TABLE security.risk_scores_new
ADD COLUMN IF NOT EXISTS event_timestamp TIMESTAMP;

-- 3. Add risk_level (LOW / MEDIUM / HIGH)
ALTER TABLE security.risk_scores_new
ADD COLUMN IF NOT EXISTS risk_level TEXT;

-- 4. Add alert_flag (whether alert generated)
ALTER TABLE security.risk_scores_new
ADD COLUMN IF NOT EXISTS alert_flag BOOLEAN DEFAULT FALSE;

-- 5. Add model_version_id (if not already added earlier)
ALTER TABLE security.risk_scores_new
ADD COLUMN IF NOT EXISTS model_version_id TEXT;

-- 6. Add feature_vector (store ML input features for debugging)
ALTER TABLE security.risk_scores_new
ADD COLUMN IF NOT EXISTS feature_vector JSONB;

UPDATE security.risk_scores_new r
SET
    anomaly_score = r.risk_score / 100.0,
    event_timestamp = r.window_start + INTERVAL '30 minutes';

UPDATE security.risk_scores_new
SET risk_level =
    CASE
        WHEN risk_score >= 80 THEN 'HIGH'
        WHEN risk_score >= 50 THEN 'MEDIUM'
        ELSE 'LOW'
    END;

UPDATE security.risk_scores_new r
SET alert_flag = TRUE
WHERE EXISTS (
    SELECT 1
    FROM security.alerts a
    WHERE a.risk_score_id = r.score_id
);

-- =====================================================
-- DB_M5 - Schema Updates for ML Prediction Storage
-- =====================================================

-- 1. Drop foreign key constraint first
ALTER TABLE security.risk_scores_new
DROP CONSTRAINT IF EXISTS risk_scores_new_model_version_id_fkey;

-- 2. Change column type to TEXT
ALTER TABLE security.risk_scores_new
ALTER COLUMN model_version_id TYPE TEXT;

-- 3. Update model version values to readable version
UPDATE security.risk_scores_new
SET model_version_id = 'v1.0'
WHERE model_version_id IS NULL
   OR model_version_id = '';

-- 4. Ensure anomaly_score = risk_score (0–1 scale)
UPDATE security.risk_scores_new
SET anomaly_score = risk_score
WHERE anomaly_score IS NULL;

-- 5. Ensure event_timestamp exists
UPDATE security.risk_scores_new
SET event_timestamp = window_start + INTERVAL '30 minutes'
WHERE event_timestamp IS NULL;

-- 6. Set risk levels based on 0–1 score
UPDATE security.risk_scores_new
SET risk_level =
    CASE
        WHEN risk_score >= 0.7 THEN 'HIGH'
        WHEN risk_score >= 0.4 THEN 'MEDIUM'
        ELSE 'LOW'
    END;

-- 7. Update alert flag
UPDATE security.risk_scores_new r
SET alert_flag = TRUE
WHERE EXISTS (
    SELECT 1
    FROM security.alerts a
    WHERE a.risk_score_id = r.score_id
);

UPDATE security.risk_scores_new
SET risk_score = anomaly_score;

UPDATE security.risk_scores_new
SET risk_level =
    CASE
        WHEN risk_score >= 0.7 THEN 'HIGH'
        WHEN risk_score >= 0.4 THEN 'MEDIUM'
        ELSE 'LOW'
    END;

UPDATE security.risk_scores_new
SET alert_flag = TRUE
WHERE anomaly_flag = TRUE;

SELECT
    user_id,
    event_timestamp,
    window_start,
    anomaly_score,
    risk_score,
    risk_level,
    anomaly_flag,
    alert_flag,
    model_version_id
FROM security.risk_scores_new
ORDER BY risk_score DESC
LIMIT 10;