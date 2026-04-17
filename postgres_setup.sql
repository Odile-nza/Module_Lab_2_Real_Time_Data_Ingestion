
-- ============================================================
-- STEP 1 — CREATE DATABASE
-- ============================================================

CREATE DATABASE ecommerce_streaming;



-- ============================================================
-- STEP 2 — CREATE EVENTS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS user_events (
    event_id        VARCHAR(36)     NOT NULL,
    user_id         INTEGER         NOT NULL,
    session_id      VARCHAR(36)     NOT NULL,
    event_type      VARCHAR(20)     NOT NULL,
    product_id      INTEGER         NOT NULL,
    product_name    VARCHAR(100)    NOT NULL,
    category        VARCHAR(50)     NOT NULL,
    price           DECIMAL(10, 2)  NOT NULL,
    quantity        INTEGER         NOT NULL DEFAULT 1,
    total_amount    DECIMAL(10, 2)  NOT NULL,
    event_timestamp TIMESTAMP       NOT NULL,
    ingested_at     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_user_events PRIMARY KEY (event_id)
);


-- ============================================================
-- STEP 3 — CREATE INDEXES FOR QUERY PERFORMANCE
-- ============================================================

-- Speed up queries filtering by user
CREATE INDEX IF NOT EXISTS idx_user_events_user_id
    ON user_events (user_id);

-- Speed up queries filtering by event type
CREATE INDEX IF NOT EXISTS idx_user_events_event_type
    ON user_events (event_type);

-- Speed up time-range queries
CREATE INDEX IF NOT EXISTS idx_user_events_timestamp
    ON user_events (event_timestamp);

-- Speed up category analytics
CREATE INDEX IF NOT EXISTS idx_user_events_category
    ON user_events (category);


-- ============================================================
-- STEP 4 — VERIFY SETUP
-- ============================================================

-- Check the table was created correctly
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_events'
ORDER BY ordinal_position;


-- ============================================================
-- USEFUL QUERIES TO MONITOR THE STREAMING PIPELINE
-- ============================================================

Total events ingested
SELECT COUNT(*) FROM user_events;

Events by type
SELECT event_type, COUNT(*) FROM user_events GROUP BY event_type;

Revenue by category
SELECT category, SUM(total_amount) AS revenue
FROM user_events
WHERE event_type = 'purchase'
GROUP BY category
ORDER BY revenue DESC;

Events per minute (throughput check)
SELECT
    DATE_TRUNC('minute', event_timestamp) AS minute,
    COUNT(*) AS events
FROM user_events
GROUP BY 1
ORDER BY 1 DESC
LIMIT 10;

Latest 5 events
SELECT * FROM user_events ORDER BY ingested_at DESC LIMIT 5;