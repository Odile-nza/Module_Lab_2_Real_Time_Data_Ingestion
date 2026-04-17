# Test Cases

## Test Environment

| Component | Value |
|-----------|-------|
| OS | Windows 11 |
| Python | 3.11 |
| PySpark | 4.1.1 |
| PostgreSQL | Neon Cloud |
| Batch size | 20 events |
| Trigger interval | 10 seconds |

---

## TC-01: CSV File Creation

**Objective:** Verify data_generator.py creates valid CSV files in data/landing/

**Steps:**
1. Run `python data_generator.py`
2. Wait 10 seconds
3. Check `data/landing/` folder

**Expected:** At least 3 CSV files, each with 20 rows and correct columns

**Actual:** Files created every 3 seconds with correct schema

**Result:** Pass

---

## TC-02: CSV Schema Validation

**Objective:** Verify CSV files contain all required columns with correct data

**Expected columns:** event_id, user_id, session_id, event_type, product_id, product_name, category, price, quantity, total_amount, timestamp

**Actual:** All 11 columns present with correct data types and formats

**Result:** Pass

---

## TC-03: Spark Detects New Files

**Objective:** Verify Spark picks up new CSV files automatically

**Steps:**
1. Start spark_streaming_to_postgres.py
2. Start data_generator.py in second terminal
3. Observe Spark logs after 10-15 seconds

**Expected:** Batch processing messages appear in Spark terminal

**Actual:** Batches processed every 10 seconds as configured

**Result:** Pass

---

## TC-04: Data Transformations

**Objective:** Verify transformations are applied correctly before writing to PostgreSQL

**Query used:**
```sql
SELECT event_timestamp, ingested_at, price, total_amount, event_type
FROM user_events LIMIT 10;
```

**Expected:** event_timestamp as proper timestamp, ingested_at populated, price rounded to 2 decimals

**Actual:** All transformations applied correctly

**Result:** Pass

---

## TC-05: Data Written to PostgreSQL

**Objective:** Verify events are stored correctly in Neon

**Query used:**
```sql
SELECT COUNT(*) FROM user_events;
SELECT event_type, COUNT(*) FROM user_events GROUP BY event_type;
```

**Expected:** Row count increases over time, view/purchase ratio ~3:1

**Actual:** 4,860 total events — 3,603 views (74.1%), 1,257 purchases (25.9%)

**Result:** Pass

---

## TC-06: No Duplicate Events

**Objective:** Verify PRIMARY KEY prevents duplicate rows on retry

**Query used:**
```sql
SELECT event_id, COUNT(*) AS cnt
FROM user_events
GROUP BY event_id
HAVING COUNT(*) > 1;
```

**Expected:** 0 duplicate rows

**Actual:** 0 duplicate rows

**Result:** Pass

---

## TC-07: Invalid Data Filtering

**Objective:** Verify invalid rows are filtered before writing to PostgreSQL

**Filters applied:**
- Null event_id, user_id, event_type, product_id — dropped
- event_type not in (view, purchase) — dropped
- price or total_amount <= 0 — dropped

**Expected:** Only valid rows reach PostgreSQL

**Actual:** All 4,860 rows in database are valid — 0 null or invalid values

**Result:** Pass

---

## TC-08: Checkpoint Resume

**Objective:** Verify pipeline resumes from checkpoint after restart without reprocessing

**Steps:**
1. Run pipeline for 30 seconds, note row count
2. Stop Spark (Ctrl+C)
3. Restart spark_streaming_to_postgres.py
4. Verify row count only increases from new files

**Expected:** No previously processed rows re-inserted

**Actual:** Checkpoint loaded correctly, no duplicates after restart

**Result:** Pass

---

## TC-09: Revenue Aggregation

**Objective:** Verify financial calculations are accurate end-to-end

**Query used:**
```sql
SELECT category,
       ROUND(SUM(total_amount)::numeric, 2) AS total_revenue,
       COUNT(*) AS purchases
FROM user_events
WHERE event_type = 'purchase'
GROUP BY category
ORDER BY total_revenue DESC;
```

**Expected:** All 6 categories present, positive revenue values rounded to 2 decimals

**Actual:** All 6 categories present, Electronics leading at $55,991.92

**Result:** Pass

---

## Summary

| Test | Description | Result |
|------|-------------|--------|
| TC-01 | CSV files created correctly | Pass |
| TC-02 | CSV schema valid | Pass |
| TC-03 | Spark detects new files | Pass |
| TC-04 | Transformations applied correctly | Pass |
| TC-05 | Data written to PostgreSQL | Pass |
| TC-06 | No duplicate events on restart | Pass |
| TC-07 | Invalid rows filtered out | Pass |
| TC-08 | Checkpoint resumes correctly | Pass |
| TC-09 | Revenue aggregation accurate | Pass |