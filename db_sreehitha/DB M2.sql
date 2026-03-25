-- ============================================================
-- MILESTONE 2
-- Daily Feature Engineering Pipeline for BehaviorGuard-AI
-- ============================================================

CREATE OR REPLACE FUNCTION features.compute_daily_features(p_feature_version INT)
RETURNS VOID AS $$
BEGIN

    -- Ensure reproducibility by clearing existing data
    DELETE FROM features.user_daily_features
    WHERE feature_version = p_feature_version;

    -- Insert aggregated daily behavioral features
    INSERT INTO features.user_daily_features (
        user_id,
        feature_date,
        login_count,
        failed_login_count,
        file_access_count,
        email_sent_count,
        external_email_count,
        http_request_count,
        after_hours_activity,
        feature_version,
        computed_at
    )
    SELECT
        u.user_id,
        d.feature_date,

        COALESCE(l.login_count, 0) AS login_count,
        COALESCE(l.failed_login_count, 0) AS failed_login_count,
        COALESCE(f.file_count, 0) AS file_access_count,
        COALESCE(e.email_count, 0) AS email_sent_count,
        COALESCE(e.external_email_count, 0) AS external_email_count,
        COALESCE(h.http_count, 0) AS http_request_count,
        COALESCE(l.after_hours_count, 0) AS after_hours_activity,

        p_feature_version,
        CURRENT_TIMESTAMP

    FROM core.users u

    -- Generate distinct activity dates
    CROSS JOIN (
        SELECT DISTINCT DATE(event_timestamp) AS feature_date FROM events.login_events
        UNION
        SELECT DISTINCT DATE(event_timestamp) FROM events.file_events
        UNION
        SELECT DISTINCT DATE(event_timestamp) FROM events.email_events
        UNION
        SELECT DISTINCT DATE(event_timestamp) FROM events.http_events
    ) d

    -- Login aggregation
    LEFT JOIN (
        SELECT
            user_id,
            DATE(event_timestamp) AS feature_date,
            COUNT(*) AS login_count,
            COUNT(*) FILTER (WHERE login_status = 'failed') AS failed_login_count,
            COUNT(*) FILTER (
                WHERE EXTRACT(HOUR FROM event_timestamp) < 9
                   OR EXTRACT(HOUR FROM event_timestamp) > 18
            ) AS after_hours_count
        FROM events.login_events
        GROUP BY user_id, DATE(event_timestamp)
    ) l
    ON u.user_id = l.user_id AND d.feature_date = l.feature_date

    -- File activity aggregation
    LEFT JOIN (
        SELECT
            user_id,
            DATE(event_timestamp) AS feature_date,
            COUNT(*) AS file_count
        FROM events.file_events
        GROUP BY user_id, DATE(event_timestamp)
    ) f
    ON u.user_id = f.user_id AND d.feature_date = f.feature_date

    -- Email activity aggregation
    LEFT JOIN (
        SELECT
            user_id,
            DATE(event_timestamp) AS feature_date,
            COUNT(*) AS email_count,
            COUNT(*) FILTER (WHERE external_recipient = TRUE) AS external_email_count
        FROM events.email_events
        GROUP BY user_id, DATE(event_timestamp)
    ) e
    ON u.user_id = e.user_id AND d.feature_date = e.feature_date

    -- HTTP activity aggregation
    LEFT JOIN (
        SELECT
            user_id,
            DATE(event_timestamp) AS feature_date,
            COUNT(*) AS http_count
        FROM events.http_events
        GROUP BY user_id, DATE(event_timestamp)
    ) h
    ON u.user_id = h.user_id AND d.feature_date = h.feature_date;

END;
$$ LANGUAGE plpgsql;