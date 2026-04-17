# ============================================================
# spark_streaming_to_postgres.py
# ============================================================

import os
import sys
import time
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================
# WINDOWS COMPATIBILITY
# ============================================================

os.environ["PYSPARK_PYTHON"]        = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
os.environ["HADOOP_HOME"]           = "C:\\hadoop"
os.environ["hadoop.home.dir"]       = "C:\\hadoop"
os.add_dll_directory("C:\\hadoop\\bin")

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
LANDING_DIR    = os.path.join(BASE_DIR, "data", "landing")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "data", "checkpoint")
ARCHIVE_DIR    = os.path.join(BASE_DIR, "data", "archive")

JDBC_URL         = os.getenv("JDBC_URL")
DB_USER          = os.getenv("DB_USER")
DB_PASSWORD      = os.getenv("DB_PASSWORD")
JDBC_DRIVER      = "org.postgresql.Driver"
DB_TABLE         = "user_events"
TRIGGER_INTERVAL = "10 seconds"

# ============================================================
# SCHEMA — must match the CSV columns from data_generator.py
# ============================================================

EVENT_SCHEMA = StructType([
    StructField("event_id",     StringType(),  nullable=False),
    StructField("user_id",      IntegerType(), nullable=False),
    StructField("session_id",   StringType(),  nullable=False),
    StructField("event_type",   StringType(),  nullable=False),
    StructField("product_id",   IntegerType(), nullable=False),
    StructField("product_name", StringType(),  nullable=False),
    StructField("category",     StringType(),  nullable=False),
    StructField("price",        DoubleType(),  nullable=False),
    StructField("quantity",     IntegerType(), nullable=False),
    StructField("total_amount", DoubleType(),  nullable=False),
    StructField("timestamp",    StringType(),  nullable=False),
])


# ============================================================
# SPARK SESSION
# ============================================================

def get_spark_session() -> SparkSession:
    """
    Creates a SparkSession configured for structured streaming
    with the PostgreSQL JDBC driver on the classpath.

    Why jars config: Spark needs the PostgreSQL JDBC driver
    to connect to the database. Maven downloads it automatically
    on first run.
    """
    spark = (
        SparkSession.builder
        .appName("EcommerceStreamingPipeline")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR)
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    logger.info(f"SparkSession started. Version: {spark.version}")
    return spark


# ============================================================
# STEP 1 — READ STREAMING DATA FROM LANDING FOLDER
# ============================================================

def read_stream(spark: SparkSession):
    """
    Sets up a streaming DataFrame that watches the landing
    folder for new CSV files.

    Why readStream instead of read:
    spark.read.csv() is a one-shot batch read.
    spark.readStream.csv() continuously monitors the folder
    and processes each new file as a micro-batch — this is
    the core of Spark Structured Streaming.

    Why explicit schema:
    Streaming sources cannot infer schema (no full scan
    of data at startup). We must define it explicitly.

    Why maxFilesPerTrigger:
    Limits how many files each micro-batch processes —
    prevents overwhelming the system if many files pile up.
    """
    os.makedirs(LANDING_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    stream_df = (
        spark.readStream
        .format("csv")
        .schema(EVENT_SCHEMA)
        .option("header", "true")
        .option("maxFilesPerTrigger", 5)
        .option("cleanSource", "archive")
        .option("sourceArchiveDir", ARCHIVE_DIR)
        .load(LANDING_DIR)
    )

    logger.info("Streaming source configured. Watching: " + LANDING_DIR)
    return stream_df


# ============================================================
# STEP 2 — TRANSFORM THE DATA
# ============================================================

def transform(df):
    """
    Applies cleaning and enrichment transformations to each
    micro-batch DataFrame before writing to PostgreSQL.

    Transformations applied:
    - Parse timestamp string to proper TimestampType
    - Filter out rows with null critical fields
    - Filter to only valid event types
    - Add ingested_at column (when Spark processed this row)
    - Ensure total_amount and price are positive
    - Round financial columns to 2 decimal places
    """
    cleaned = (
        df
        .withColumn(
            "event_timestamp",
            F.to_timestamp(F.col("timestamp"), "yyyy-MM-dd HH:mm:ss")
        )
        .drop("timestamp")
        .withColumn("ingested_at", F.current_timestamp())
        .filter(
            F.col("event_id").isNotNull() &
            F.col("user_id").isNotNull() &
            F.col("event_type").isNotNull() &
            F.col("product_id").isNotNull()
        )
        .filter(F.col("event_type").isin("view", "purchase"))
        .filter(
            (F.col("price") > 0) &
            (F.col("total_amount") > 0)
        )
        .withColumn("price",        F.round(F.col("price"), 2))
        .withColumn("total_amount", F.round(F.col("total_amount"), 2))
    )

    return cleaned


# ============================================================
# STEP 3 — WRITE EACH MICRO-BATCH TO POSTGRESQL
# ============================================================

def write_batch_to_postgres(batch_df, batch_id: int) -> None:
    """
    Writes one micro-batch DataFrame to the PostgreSQL table.

    Why foreachBatch instead of a direct writeStream sink:
    foreachBatch gives us full control over how each
    micro-batch is written — we can log per-batch metrics,
    handle errors gracefully, and write to multiple sinks.

    Why mode("append"):
    Streaming always appends. The PRIMARY KEY on event_id
    in PostgreSQL prevents duplicates if a batch is replayed.
    """
    count = batch_df.count()

    if count == 0:
        logger.info(f"Batch {batch_id}: empty, skipping.")
        return

    start = time.time()

    try:
        (
            batch_df.write
            .format("jdbc")
            .option("url",            JDBC_URL)
            .option("dbtable",        DB_TABLE)
            .option("user",           DB_USER)
            .option("password",       DB_PASSWORD)
            .option("driver",         JDBC_DRIVER)
            .option("ssl",            "true")
            .option("sslmode",        "require")
            .option("batchsize",      1000)
            .option("numPartitions",  2)
            .option("isolationLevel", "READ_COMMITTED")
            .mode("append")
            .save()
        )

        elapsed    = round(time.time() - start, 2)
        throughput = round(count / elapsed, 1) if elapsed > 0 else 0

        logger.info(
            f"Batch {batch_id} written: "
            f"{count} rows in {elapsed}s "
            f"({throughput} rows/sec)"
        )

    except Exception as e:
        logger.error(f"Batch {batch_id} failed: {e}")
        raise


# ============================================================
# MAIN — START THE STREAMING JOB
# ============================================================

def main():
    """
    Entry point. Starts the Spark Structured Streaming job
    and keeps it running until manually stopped (Ctrl+C)
    or until the stream terminates.

    Pipeline:
        readStream (CSV folder)
            -> transform (clean + enrich)
            -> foreachBatch (write to PostgreSQL)
            -> awaitTermination (keep alive)
    """
    logger.info("=" * 60)
    logger.info("ECOMMERCE STREAMING PIPELINE STARTED")
    logger.info("=" * 60)

    spark = get_spark_session()

    try:
        raw_stream       = read_stream(spark)
        processed_stream = transform(raw_stream)

        query = (
            processed_stream.writeStream
            .foreachBatch(write_batch_to_postgres)
            .outputMode("append")
            .trigger(processingTime=TRIGGER_INTERVAL)
            .option("checkpointLocation", CHECKPOINT_DIR)
            .start()
        )

        logger.info(f"Stream started. Trigger: every {TRIGGER_INTERVAL}")
        logger.info("Waiting for new CSV files in data/landing/")
        logger.info("Press Ctrl+C to stop.\n")

        query.awaitTermination()

    except KeyboardInterrupt:
        logger.info("Streaming pipeline stopped by user.")

    finally:
        spark.stop()
        logger.info("SparkSession stopped.")


if __name__ == "__main__":
    main()