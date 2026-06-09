-- =====================================================
-- BehaviorGuard-AI
-- Milestone 7: Swap partitioned tables and fix schema
-- =====================================================

-- Add partitions for March and April 2026 for features
CREATE TABLE IF NOT EXISTS features.user_behavior_features_2026_03
PARTITION OF features.user_behavior_features
FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS features.user_behavior_features_2026_04
PARTITION OF features.user_behavior_features
FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Swap risk_scores tables
ALTER TABLE security.risk_scores RENAME TO risk_scores_old;
ALTER TABLE security.risk_scores_new RENAME TO risk_scores;

-- Add partitions for March and April 2026 for risk_scores
CREATE TABLE IF NOT EXISTS security.risk_scores_2026_03
PARTITION OF security.risk_scores
FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS security.risk_scores_2026_04
PARTITION OF security.risk_scores
FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
