# User Guide — Running the Streaming Pipeline

## Prerequisites

Before running the project, ensure the following are installed:

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.9+ | `python --version` |
| Java | 11 | `java -version` |
| PostgreSQL | 14+ | `psql --version` |
| pip | latest | `pip --version` |

**Windows users:** Ensure `winutils.exe` is in `C:\hadoop\bin\` and `HADOOP_HOME` is set (the script handles this automatically).

---

## Step 1 — Clone and Set Up the Project

```bash
git clone https://github.com/Odile-nza/Module_Lab_2_Real_Time_Data_Ingestion.git
cd Module_Lab_2_Real_Time_Data_Ingestion

python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

**`requirements.txt` contents:**
```
pyspark>=3.3.0
faker>=19.0.0
pandas>=1.5.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
```

---

## Step 2 — Set Up PostgreSQL

### 2a. Start PostgreSQL
```bash
# Mac (Homebrew)
brew services start postgresql

# Windows — start via pgAdmin or Services panel

# Linux
sudo systemctl start postgresql
```

### 2b. Create the database and table
```bash
psql -U postgres -f postgres_setup.sql
```

Or manually in psql:
```sql
CREATE DATABASE ecommerce_streaming;
\c ecommerce_streaming
\i postgres_setup.sql
```

### 2c. Verify the table was created
```sql
\c ecommerce_streaming
\dt
SELECT * FROM user_events LIMIT 5;
```

---

## Step 3 — Update Connection Details

Open `spark_streaming_to_postgres.py` and update these lines:

```python
JDBC_URL    = "jdbc:postgresql://localhost:5432/ecommerce_streaming"
DB_USER     = "postgres"
DB_PASSWORD = "your_actual_password_here"
```

Also update `postgres_connection_details.txt` with the same values.

---

## Step 4 — Create Required Folders

```bash
mkdir -p data/landing data/archive data/checkpoint
```

---

## Step 5 — Open Two Terminals

You need **two terminals running simultaneously**.

### Terminal 1 — Start the Spark Streaming Job
```bash
cd ecommerce-streaming
venv\Scripts\activate           # Windows
source venv/bin/activate        # Mac/Linux

python spark_streaming_to_postgres.py
```

Wait until you see:
```
SparkSession started. Version: 4.x.x
Stream started. Trigger: every 10 seconds
Waiting for new CSV files in data/landing/
```

### Terminal 2 — Start the Data Generator
```bash
cd ecommerce-streaming
venv\Scripts\activate           # Windows
source venv/bin/activate        # Mac/Linux

python data_generator.py
```

You should see:
```
2024-04-15 12:00:00 | INFO | Data generator started.
2024-04-15 12:00:00 | INFO | Writing to: data/landing
2024-04-15 12:00:03 | INFO | Batch 0001 saved: events_batch_0001_... | 15 views, 5 purchases
2024-04-15 12:00:06 | INFO | Batch 0002 saved: events_batch_0002_... | 14 views, 6 purchases
```

---

## Step 6 — Verify Data in PostgreSQL

Open a third terminal and connect to PostgreSQL:

```bash
psql -U postgres -d ecommerce_streaming
```

Run these queries to verify data is flowing:

```sql
-- Total events ingested
SELECT COUNT(*) FROM user_events;

-- Events by type
SELECT event_type, COUNT(*)
FROM user_events
GROUP BY event_type;

-- Revenue by category
SELECT category, ROUND(SUM(total_amount)::numeric, 2) AS revenue
FROM user_events
WHERE event_type = 'purchase'
GROUP BY category
ORDER BY revenue DESC;

-- Latest 5 events
SELECT event_id, user_id, event_type, product_name, total_amount, event_timestamp
FROM user_events
ORDER BY ingested_at DESC
LIMIT 5;
```

---

## Step 7 — Stop the Pipeline

Press `Ctrl+C` in both terminals to stop the generator and the streaming job gracefully.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `HADOOP_HOME not set` | winutils missing | Download winutils.exe to `C:\hadoop\bin\` |
| `Connection refused` on JDBC | PostgreSQL not running | Start PostgreSQL service |
| `password authentication failed` | Wrong password in config | Update `DB_PASSWORD` in streaming script |
| `Table doesn't exist` | SQL setup not run | Run `postgres_setup.sql` first |
| `Faker not found` | Missing dependency | Run `pip install faker` |
| No data in PostgreSQL | Trigger not fired yet | Wait 10 seconds for first trigger |
| `java.lang.ClassNotFoundException: org.postgresql.Driver` | JDBC jar not downloaded | Let Spark download it via `spark.jars.packages` on first run (needs internet) |

---

## Project File Reference

| File | Purpose |
|------|---------|
| `data_generator.py` | Generates fake CSV events continuously |
| `spark_streaming_to_postgres.py` | Spark streaming job — reads, transforms, writes |
| `postgres_setup.sql` | Creates database and table |
| `postgres_connection_details.txt` | Connection reference |
| `data/landing/` | CSV files drop zone (Spark watches here) |
| `data/archive/` | Processed files moved here automatically |
| `data/checkpoint/` | Spark streaming checkpoint state |
| `docs/` | Documentation files |