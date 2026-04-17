# Project Overview — Real-Time E-Commerce Streaming Pipeline

## Summary

This project builds a real-time data ingestion pipeline that simulates an e-commerce platform tracking user activity. Fake user events (product views and purchases) are generated continuously, streamed using Apache Spark Structured Streaming, and stored in a PostgreSQL database for analysis.

---

## System Architecture

```
┌─────────────────────┐        CSV files         ┌──────────────────────────┐
│                     │  ──────────────────────►  │                          │
│  data_generator.py  │   (every 3 seconds)       │   data/landing/  folder  │
│                     │                           │                          │
│  Generates 20 fake  │                           │  Spark watches this      │
│  events per batch   │                           │  folder continuously     │
│  using Faker        │                           │                          │
└─────────────────────┘                           └────────────┬─────────────┘
                                                               │
                                                               │ readStream
                                                               ▼
                                                  ┌────────────────────────────┐
                                                  │                            │
                                                  │  Spark Structured          │
                                                  │  Streaming                 │
                                                  │                            │
                                                  │  • Read CSV with schema    │
                                                  │  • Parse timestamp         │
                                                  │  • Filter invalid rows     │
                                                  │  • Round financials        │
                                                  │  • Add ingested_at         │
                                                  │                            │
                                                  └────────────┬───────────────┘
                                                               │
                                                               │ foreachBatch (JDBC)
                                                               ▼
                                                  ┌────────────────────────────┐
                                                  │                            │
                                                  │  PostgreSQL                │
                                                  │  ecommerce_streaming DB    │
                                                  │  user_events table         │
                                                  │                            │
                                                  │  PRIMARY KEY on event_id   │
                                                  │  → idempotent writes       │
                                                  │                            │
                                                  └────────────────────────────┘
```

---

## Components

### 1. `data_generator.py` — Data Source
Simulates an e-commerce platform by generating fake user events using the `Faker` library. Each batch produces 20 events (a mix of `view` and `purchase` actions across 10 products) and saves them as a timestamped CSV file in `data/landing/`. A new file is written every 3 seconds.

**Event fields generated:**
| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Unique event identifier |
| `user_id` | Integer | Simulated user (1–500) |
| `session_id` | UUID | Groups events in one browsing session |
| `event_type` | String | `view` or `purchase` (3:1 ratio) |
| `product_id` | Integer | Product reference (1–10) |
| `product_name` | String | Product display name |
| `category` | String | Product category |
| `price` | Float | Unit price in USD |
| `quantity` | Integer | Units (purchases only; views = 1) |
| `total_amount` | Float | price × quantity |
| `timestamp` | String | Event time as `YYYY-MM-DD HH:MM:SS` |

### 2. `spark_streaming_to_postgres.py` — Stream Processor
A Spark Structured Streaming job that continuously monitors `data/landing/` for new CSV files. Each micro-batch is triggered every 10 seconds, processed through a transformation pipeline, and written to PostgreSQL via JDBC.

**Transformations applied:**
- Parse `timestamp` string → proper `TimestampType`
- Add `ingested_at` (processing time) column
- Filter rows with null critical fields
- Filter invalid event types
- Validate price and total_amount are positive
- Round financial columns to 2 decimal places

**Key Spark concepts used:**
- `readStream` — continuously monitors the folder
- `foreachBatch` — custom write logic per micro-batch
- `checkpointLocation` — enables fault tolerance and exactly-once processing
- `cleanSource=archive` — moves processed files to `data/archive/` to avoid reprocessing

### 3. `postgres_setup.sql` — Database Setup
Creates the `ecommerce_streaming` database and `user_events` table with appropriate data types, constraints, and indexes. The `PRIMARY KEY` on `event_id` ensures idempotency — replaying a batch never creates duplicate rows.

---

## Data Flow

```
1. data_generator.py runs in Terminal 1
   └─ Writes events_batch_0001_20240415_120000.csv to data/landing/

2. Spark detects new file (every 10 second trigger)
   └─ Reads file using defined schema

3. Spark applies transformations
   └─ Cleans, casts types, enriches with ingested_at

4. foreachBatch writes to PostgreSQL
   └─ JDBC INSERT into user_events table

5. File moved to data/archive/ (cleanSource)
   └─ Prevents reprocessing on restart

6. Checkpoint saved to data/checkpoint/
   └─ Spark knows where it left off if it crashes
```

---

## Key Design Decisions

**Why CSV files as the streaming source?**
CSV files simulate the "drop zone" pattern used in real data lakes — upstream systems drop files into a folder and the streaming job picks them up. In production this would be replaced by Kafka.

**Why `foreachBatch` instead of a direct JDBC sink?**
`foreachBatch` gives full control — we can log per-batch metrics, handle errors gracefully, and write to multiple sinks from the same stream.

**Why `checkpointLocation`?**
Checkpointing records which files have been processed. If the Spark job crashes and restarts, it resumes from where it left off without reprocessing already-written data.

**Why `PRIMARY KEY` on `event_id`?**
Guarantees idempotency — the same event can be written twice (on retry) without creating a duplicate row in PostgreSQL.