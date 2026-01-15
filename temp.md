WITH ydtx_users AS (
    -- YDTX 渠道：2025-12-01 到 2025-12-15 注册的用户
    SELECT DISTINCT
        user_id,
        DATE(create_time) AS register_date,
        'YDTX' AS channel
    FROM mysql.ad_user_log
    WHERE source = 'YDTX'
      AND DATE(create_time) BETWEEN DATE '2025-12-01' AND DATE '2025-12-15'
),
google_users AS (
    -- Google 渠道：2025-12-01 到 2025-12-15 注册的用户
    SELECT DISTINCT
        user_id,
        DATE(create_time) AS register_date,
        'Google' AS channel
    FROM mysql.ad_user_log
    WHERE source = 'Google'
      AND DATE(create_time) BETWEEN DATE '2025-12-01' AND DATE '2025-12-15'
),
impact_users AS (
    -- Impact 渠道：2025-12-01 到 2025-12-15 注册的用户
    SELECT DISTINCT
        user_id,
        DATE(create_time) AS register_date,
        'Impact' AS channel
    FROM mysql.ad_user_log
    WHERE source = 'Impact'
      AND p1 = '6049004'
      AND DATE(create_time) BETWEEN DATE '2025-12-01' AND DATE '2025-12-15'
),
all_users AS (
    -- 合并三个渠道的用户
    SELECT * FROM ydtx_users
    UNION ALL
    SELECT * FROM google_users
    UNION ALL
    SELECT * FROM impact_users
),
user_active_days AS (
    -- 统计每个用户在"注册日当天起，15 天内"的活跃天数
    SELECT
        u.user_id,
        u.channel,
        COUNT(
            DISTINCT DATE(
                TIMESTAMP 'epoch' + c.create_timestamp * INTERVAL '1 second'
            )
        ) AS active_days
    FROM all_users u
    LEFT JOIN pgsql.completion_logs c
        ON c.user_id = u.user_id
       AND c.status = 'success'
       AND DATE(
            TIMESTAMP 'epoch' + c.create_timestamp * INTERVAL '1 second'
           )
           BETWEEN u.register_date
               AND (u.register_date + INTERVAL '14 day')
    GROUP BY u.user_id, u.channel
),
capped_active_days AS (
    -- 把活跃天数截断到 0~15
    SELECT
        user_id,
        channel,
        CASE 
            WHEN active_days < 0 THEN 0
            WHEN active_days > 15 THEN 15
            ELSE active_days
        END AS active_days_0_15
    FROM user_active_days
),
channel_stats AS (
    -- 按渠道和活跃天数分组统计
    SELECT
        channel,
        active_days_0_15,
        COUNT(*) AS user_count
    FROM capped_active_days
    GROUP BY channel, active_days_0_15
),
channel_totals AS (
    -- 计算每个渠道的总用户数
    SELECT
        channel,
        SUM(user_count) AS total_users
    FROM channel_stats
    GROUP BY channel
)
-- 最终输出：透视表格式
SELECT
    COALESCE(y.active_days_0_15, g.active_days_0_15, i.active_days_0_15) AS active_days,
    COALESCE(y.user_count, 0) AS ydtx_user_count,
    ROUND(COALESCE(y.user_count * 100.0 / yt.total_users, 0), 2) AS ydtx_percentage,
    COALESCE(g.user_count, 0) AS google_user_count,
    ROUND(COALESCE(g.user_count * 100.0 / gt.total_users, 0), 2) AS google_percentage,
    COALESCE(i.user_count, 0) AS impact_user_count,
    ROUND(COALESCE(i.user_count * 100.0 / it.total_users, 0), 2) AS impact_percentage
FROM (
    SELECT active_days_0_15, user_count FROM channel_stats WHERE channel = 'YDTX'
) y
FULL OUTER JOIN (
    SELECT active_days_0_15, user_count FROM channel_stats WHERE channel = 'Google'
) g ON y.active_days_0_15 = g.active_days_0_15
FULL OUTER JOIN (
    SELECT active_days_0_15, user_count FROM channel_stats WHERE channel = 'Impact'
) i ON COALESCE(y.active_days_0_15, g.active_days_0_15) = i.active_days_0_15
CROSS JOIN (SELECT total_users FROM channel_totals WHERE channel = 'YDTX') yt
CROSS JOIN (SELECT total_users FROM channel_totals WHERE channel = 'Google') gt
CROSS JOIN (SELECT total_users FROM channel_totals WHERE channel = 'Impact') it
ORDER BY active_days;