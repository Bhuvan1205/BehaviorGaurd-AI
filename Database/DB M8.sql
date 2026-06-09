-- =====================================================
-- BehaviorGuard-AI
-- Milestone 8: Recreate flat tables for Phase 2 batch processing pipeline
-- =====================================================

-- Drop partitioned/old tables and their associated dependencies
DROP TABLE IF EXISTS security.risk_scores_old CASCADE;
DROP TABLE IF EXISTS security.risk_scores CASCADE;
DROP TABLE IF EXISTS features.user_behavior_features CASCADE;
DROP TABLE IF EXISTS security.alerts CASCADE;

-- Create flat security.risk_scores table
CREATE TABLE security.risk_scores (
    score_id           BIGSERIAL PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date         DATE DEFAULT CURRENT_DATE,
    window_start       TIMESTAMP NOT NULL,
    shift              VARCHAR(10) DEFAULT 'Day',
    role_group         VARCHAR(50) DEFAULT 'general',
    cluster_id         INTEGER,
    hdbscan_label      INTEGER,
    is_noise           BOOLEAN DEFAULT FALSE,
    if_score           DOUBLE PRECISION,
    risk_score         DOUBLE PRECISION,
    risk_level         VARCHAR(20),
    anomaly_flag       BOOLEAN DEFAULT FALSE,
    alert_flag         BOOLEAN DEFAULT FALSE,
    feature_vector     JSONB,
    cluster_probability DOUBLE PRECISION DEFAULT 1.0,
    if_anomaly         BOOLEAN DEFAULT FALSE,
    created_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_user_date ON security.risk_scores (user_id, batch_date);
CREATE INDEX IF NOT EXISTS idx_risk_anomaly   ON security.risk_scores (anomaly_flag);
CREATE INDEX IF NOT EXISTS idx_risk_batch     ON security.risk_scores (batch_date DESC);

-- Create flat features.user_behavior_features table
CREATE TABLE features.user_behavior_features (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date         DATE DEFAULT CURRENT_DATE,
    window_start       TIMESTAMP NOT NULL,
    logon_count        INTEGER DEFAULT 0,
    logoff_count       INTEGER DEFAULT 0,
    unique_pcs         INTEGER DEFAULT 0,
    hour               INTEGER DEFAULT 0,
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

CREATE INDEX IF NOT EXISTS idx_features_user_date ON features.user_behavior_features (user_id, batch_date);

-- Recreate security.alerts (flat / batch-oriented)
CREATE TABLE security.alerts (
    alert_id           BIGSERIAL PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES core.users(user_id) ON DELETE CASCADE,
    batch_date         DATE DEFAULT CURRENT_DATE,
    anomaly_count      INTEGER DEFAULT 1,
    window_days        INTEGER DEFAULT 7,
    severity           VARCHAR(20) DEFAULT 'HIGH',
    status             VARCHAR(20) DEFAULT 'OPEN',
    email_analysis_triggered BOOLEAN DEFAULT FALSE,
    risk_score_id      BIGINT, -- for backward compatibility / seed_demo_data
    created_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_user   ON security.alerts (user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON security.alerts (status);
