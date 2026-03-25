-- =====================================================
-- BehaviorGuard-AI
-- Milestone 4: Alert Generation
-- =====================================================

INSERT INTO security.alerts (
    user_id,
    risk_score_id,
    severity,
    status
)

SELECT
    r.user_id,
    r.score_id,
    'HIGH' AS severity,
    'OPEN' AS status

FROM security.risk_scores r

-- Select only the latest risk score for each user
WHERE r.score_id IN (
    SELECT MAX(score_id)
    FROM security.risk_scores
    GROUP BY user_id
)

-- Only create alerts for anomalous users
AND r.anomaly_flag = TRUE

-- Prevent duplicate alerts
AND NOT EXISTS (
    SELECT 1
    FROM security.alerts a
    WHERE a.risk_score_id = r.score_id
);

