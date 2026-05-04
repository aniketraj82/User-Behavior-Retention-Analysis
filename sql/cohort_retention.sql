-- Signup-month cohort retention.
-- A user is retained in a month if they have at least one engagement event in that month.

WITH signup_cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM users
),

monthly_activity AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('month', event_time)::date AS activity_month
    FROM events
    WHERE event_type IN ('session_start', 'feature_used', 'report_viewed', 'project_updated')
),

cohort_activity AS (
    SELECT
        s.cohort_month,
        m.activity_month,
        (
            DATE_PART('year', m.activity_month) * 12 + DATE_PART('month', m.activity_month)
            - DATE_PART('year', s.cohort_month) * 12 - DATE_PART('month', s.cohort_month)
        )::int AS months_since_signup,
        COUNT(DISTINCT s.user_id) AS active_users
    FROM signup_cohorts s
    JOIN monthly_activity m
        ON s.user_id = m.user_id
        AND m.activity_month >= s.cohort_month
    GROUP BY 1, 2, 3
),

cohort_size AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT user_id) AS cohort_users
    FROM signup_cohorts
    GROUP BY cohort_month
)

SELECT
    a.cohort_month,
    a.months_since_signup,
    c.cohort_users,
    a.active_users,
    ROUND(a.active_users::numeric / NULLIF(c.cohort_users, 0), 4) AS retention_rate
FROM cohort_activity a
JOIN cohort_size c
    ON a.cohort_month = c.cohort_month
ORDER BY a.cohort_month, a.months_since_signup;
