-- Monthly churn based on explicit churn events and prior active users.

WITH monthly_active AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('month', event_time)::date AS activity_month
    FROM events
    WHERE event_type IN ('session_start', 'feature_used', 'report_viewed', 'project_updated')
),

monthly_churn AS (
    SELECT
        DATE_TRUNC('month', event_time)::date AS churn_month,
        COUNT(DISTINCT user_id) AS churned_users
    FROM events
    WHERE event_type = 'churned'
    GROUP BY 1
),

active_base AS (
    SELECT
        activity_month,
        COUNT(DISTINCT user_id) AS active_users,
        LAG(COUNT(DISTINCT user_id)) OVER (ORDER BY activity_month) AS prior_month_active_users
    FROM monthly_active
    GROUP BY 1
)

SELECT
    a.activity_month,
    a.active_users,
    a.prior_month_active_users,
    COALESCE(c.churned_users, 0) AS churned_users,
    ROUND(COALESCE(c.churned_users, 0)::numeric / NULLIF(a.prior_month_active_users, 0), 4) AS churn_rate
FROM active_base a
LEFT JOIN monthly_churn c
    ON a.activity_month = c.churn_month
ORDER BY a.activity_month;
