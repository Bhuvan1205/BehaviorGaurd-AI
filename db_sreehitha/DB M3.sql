-- =====================================================
-- BehaviorGuard-AI
-- Milestone 3: Risk Scoring Engine
-- Computes behavioral risk scores from event activity
-- =====================================================

-- 1️⃣ Aggregate login behavior
WITH login_stats AS (
    SELECT
        user_id,
        COUNT(*) AS login_count,
        COUNT(*) FILTER (WHERE login_status = 'failed') AS failed_logins
    FROM events.login_events
    GROUP BY user_id
),

-- 2️⃣ Aggregate file access behavior
file_stats AS (
    SELECT
        user_id,
        COUNT(*) AS file_access_count
    FROM events.file_events
    GROUP BY user_id
),

-- 3️⃣ Aggregate email behavior
email_stats AS (
    SELECT
        user_id,
        COUNT(*) AS email_count,
        COUNT(*) FILTER (WHERE external_recipient = TRUE) AS external_emails
    FROM events.email_events
    GROUP BY user_id
),

-- 4️⃣ Aggregate web activity
http_stats AS (
    SELECT
        user_id,
        COUNT(*) AS http_requests
    FROM events.http_events
    GROUP BY user_id
),

-- 5️⃣ Combine all behavioral features
combined_features AS (
    SELECT
        u.user_id,
        COALESCE(l.failed_logins,0) AS failed_logins,
        COALESCE(f.file_access_count,0) AS file_access_count,
        COALESCE(e.external_emails,0) AS external_emails,
        COALESCE(h.http_requests,0) AS http_requests
    FROM core.users u
    LEFT JOIN login_stats l ON u.user_id = l.user_id
    LEFT JOIN file_stats f ON u.user_id = f.user_id
    LEFT JOIN email_stats e ON u.user_id = e.user_id
    LEFT JOIN http_stats h ON u.user_id = h.user_id
)

-- 6️⃣ Insert calculated risk scores
INSERT INTO security.risk_scores (
    user_id,
    model_version_id,
    score_timestamp,
    risk_score,
    anomaly_flag
)

SELECT
    cf.user_id,
    (SELECT version_id FROM ml.model_versions ORDER BY created_at DESC LIMIT 1),
    NOW(),

    -- Risk score calculation
    (
        cf.failed_logins * 3 +
        cf.external_emails * 4 +
        cf.file_access_count * 1.5 +
        cf.http_requests * 0.5
    ) AS risk_score,

    -- Anomaly detection rule
    CASE
        WHEN (
            cf.failed_logins * 3 +
            cf.external_emails * 4 +
            cf.file_access_count * 1.5 +
            cf.http_requests * 0.5
        ) > 60 THEN TRUE
        ELSE FALSE
    END

FROM combined_features cf;