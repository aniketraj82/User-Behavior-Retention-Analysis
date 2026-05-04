-- Daily Active Users and Monthly Active Users.
-- Excludes non-engagement account events so signup and churn events do not inflate activity.

WITH engagement_events AS (
    SELECT
        user_id,
        CAST(event_time AS DATE) AS activity_date,
        DATE_TRUNC('month', event_time)::date AS activity_month
    FROM events
    WHERE event_type IN ('session_start', 'feature_used', 'report_viewed', 'project_updated')
),

dau AS (
    SELECT
        activity_date,
        COUNT(DISTINCT user_id) AS dau
    FROM engagement_events
    GROUP BY activity_date
),

mau AS (
    SELECT
        activity_month,
        COUNT(DISTINCT user_id) AS mau
    FROM engagement_events
    GROUP BY activity_month
)

SELECT
    d.activity_date,
    d.dau,
    m.activity_month,
    m.mau,
    ROUND(d.dau::numeric / NULLIF(m.mau, 0), 4) AS dau_mau_stickiness
FROM dau d
JOIN mau m
    ON DATE_TRUNC('month', d.activity_date)::date = m.activity_month
ORDER BY d.activity_date;
