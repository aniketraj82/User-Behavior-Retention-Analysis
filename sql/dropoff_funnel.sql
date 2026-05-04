-- Activation funnel by acquisition channel.

WITH user_stages AS (
    SELECT
        u.user_id,
        u.channel,
        MAX(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END) AS signed_up,
        MAX(CASE WHEN e.event_type = 'onboarding_completed' THEN 1 ELSE 0 END) AS onboarded,
        MAX(CASE WHEN e.event_type = 'first_key_action' THEN 1 ELSE 0 END) AS first_key_action,
        MAX(CASE WHEN e.event_type IN ('session_start', 'feature_used', 'report_viewed', 'project_updated') THEN 1 ELSE 0 END) AS became_active
    FROM users u
    LEFT JOIN events e
        ON u.user_id = e.user_id
    GROUP BY 1, 2
)

SELECT
    channel,
    COUNT(*) AS signed_up_users,
    SUM(onboarded) AS onboarded_users,
    SUM(first_key_action) AS first_key_action_users,
    SUM(became_active) AS active_users,
    ROUND(SUM(onboarded)::numeric / NULLIF(COUNT(*), 0), 4) AS onboarding_rate,
    ROUND(SUM(first_key_action)::numeric / NULLIF(COUNT(*), 0), 4) AS key_action_rate,
    ROUND(SUM(became_active)::numeric / NULLIF(COUNT(*), 0), 4) AS activation_rate,
    ROUND(1 - SUM(first_key_action)::numeric / NULLIF(COUNT(*), 0), 4) AS dropoff_before_key_action
FROM user_stages
GROUP BY channel
ORDER BY dropoff_before_key_action DESC;
