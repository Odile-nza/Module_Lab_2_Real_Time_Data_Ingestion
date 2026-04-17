# Performance Metrics

## Test Configuration

| Parameter | Value |
|-----------|-------|
| PySpark version | 4.1.1 |
| Batch size | 20 events per CSV file |
| Trigger interval | 10 seconds |
| Generator interval | 3 seconds per file |
| Database | Neon PostgreSQL (cloud) |
| Test duration | ~8 minutes |

---

## Latency

| Metric | Value |
|--------|-------|
| Average | 17.87s |
| Minimum | 1.69s |
| Maximum | 27.07s |

> Latency is bounded by the 10s trigger interval plus cloud JDBC overhead.

---

## Throughput & Data Quality

| Metric | Value |
|--------|-------|
| Total events ingested | 4,860 |
| Views | 3,603 (74.1%) |
| Purchases | 1,257 (25.9%) |
| Duplicates | 0 |
| Null/invalid rows | 0 |

---

## Revenue by Category

| Category | Revenue (USD) | Purchases |
|----------|--------------|-----------|
| Electronics | $55,991.92 | 400 |
| Sports | $24,762.58 | 360 |
| Kitchen | $13,047.39 | 135 |
| Books | $9,167.38 | 125 |
| Stationery | $2,677.32 | 128 |
| Home | $4,417.79 | 109 |

---

## KPI Summary

| KPI | Target | Actual |
|-----|--------|--------|
| Throughput | >= 5 events/sec | ~10 events/sec |
| Average latency | <= 20s | 17.87s |
| Max latency | <= 30s | 27.07s |
| Duplicate rate | 0% | 0% |
| Data quality | 100% clean | 100% clean |