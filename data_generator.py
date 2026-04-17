# ============================================================
# data_generator.py
# ============================================================
# Simulates an e-commerce platform by generating fake user
# events (views and purchases) and saving them as CSV files
# into the data/landing/ folder every few seconds.
#
# Spark Structured Streaming watches that folder and picks up
# each new file as it arrives — simulating real-time ingestion.
# ============================================================

import os
import time
import uuid
import random
import logging
import pandas as pd

from datetime import datetime
from faker import Faker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

fake = Faker()

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LANDING_DIR = os.path.join(BASE_DIR, "data", "landing")
EVENTS_PER_BATCH = 20                   
BATCH_INTERVAL   = 3                    
MAX_BATCHES      = None                 

# ============================================================
# PRODUCT CATALOGUE
# ============================================================

PRODUCTS = [
    {"product_id": 1,  "product_name": "Wireless Headphones",  "category": "Electronics", "price": 79.99},
    {"product_id": 2,  "product_name": "Running Shoes",         "category": "Sports",      "price": 59.99},
    {"product_id": 3,  "product_name": "Coffee Maker",          "category": "Kitchen",     "price": 49.99},
    {"product_id": 4,  "product_name": "Python Programming Book","category": "Books",      "price": 34.99},
    {"product_id": 5,  "product_name": "Yoga Mat",              "category": "Sports",      "price": 24.99},
    {"product_id": 6,  "product_name": "Bluetooth Speaker",     "category": "Electronics", "price": 39.99},
    {"product_id": 7,  "product_name": "Desk Lamp",             "category": "Home",        "price": 19.99},
    {"product_id": 8,  "product_name": "Water Bottle",          "category": "Sports",      "price": 14.99},
    {"product_id": 9,  "product_name": "Mechanical Keyboard",   "category": "Electronics", "price": 89.99},
    {"product_id": 10, "product_name": "Notebook Set",          "category": "Stationery",  "price": 9.99},
]

EVENT_TYPES = ["view", "view", "view", "purchase"]  


# ============================================================
# GENERATE A SINGLE EVENT
# ============================================================

def generate_event(session_id: str) -> dict:
    """
    Generates one fake e-commerce event.

    Why session_id as a parameter: multiple events in a batch
    share the same session — simulating a user browsing
    through multiple products in one session.

    Returns:
        dict: One event record with all required fields.
    """
    product    = random.choice(PRODUCTS)
    event_type = random.choice(EVENT_TYPES)
    quantity   = random.randint(1, 3) if event_type == "purchase" else 1

    return {
        "event_id":    str(uuid.uuid4()),
        "user_id":     random.randint(1, 500),
        "session_id":  session_id,
        "event_type":  event_type,
        "product_id":  product["product_id"],
        "product_name":product["product_name"],
        "category":    product["category"],
        "price":       product["price"],
        "quantity":    quantity,
        "total_amount":round(product["price"] * quantity, 2),
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============================================================
# GENERATE ONE BATCH AND SAVE AS CSV
# ============================================================

def generate_batch(batch_num: int) -> str:
    """
    Generates EVENTS_PER_BATCH events, saves them as a
    timestamped CSV file in the landing directory.

    Why timestamped filenames: Spark reads files in order
    and a unique name prevents overwriting previous batches.

    Args:
        batch_num (int): Sequential batch counter for logging.

    Returns:
        str: Path to the saved CSV file.
    """
    # Each batch = one user session (same session_id)
    session_id = str(uuid.uuid4())
    events     = [generate_event(session_id) for _ in range(EVENTS_PER_BATCH)]

    df        = pd.DataFrame(events)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename  = f"events_batch_{batch_num:04d}_{timestamp}.csv"
    filepath  = os.path.join(LANDING_DIR, filename)

    df.to_csv(filepath, index=False)

    purchase_count = len(df[df["event_type"] == "purchase"])
    view_count     = len(df[df["event_type"] == "view"])

    logger.info(
        f"Batch {batch_num:04d} saved: {filename} "
        f"| {view_count} views, {purchase_count} purchases"
    )
    return filepath


# ============================================================
# MAIN — RUN THE GENERATOR
# ============================================================

def main():
    """
    Continuously generates CSV event batches into the landing
    folder. Run this in one terminal while Spark streams in
    another terminal.

    Press Ctrl+C to stop.
    """
    os.makedirs(LANDING_DIR, exist_ok=True)
    logger.info(f"Data generator started.")
    logger.info(f"Writing to: {LANDING_DIR}")
    logger.info(f"Batch size: {EVENTS_PER_BATCH} events every {BATCH_INTERVAL}s")
    logger.info("Press Ctrl+C to stop.\n")

    batch_num   = 1
    total_events = 0

    try:
        while MAX_BATCHES is None or batch_num <= MAX_BATCHES:
            generate_batch(batch_num)
            total_events += EVENTS_PER_BATCH
            logger.info(f"Total events generated so far: {total_events}")
            batch_num += 1
            time.sleep(BATCH_INTERVAL)

    except KeyboardInterrupt:
        logger.info(f"\nGenerator stopped. Total batches: {batch_num - 1}, Total events: {total_events}")


if __name__ == "__main__":
    main()