
import logging
import sqlite3
import time
from datetime import datetime, timezone

from monitor import (
    DB_PATH,
    SAMPLE_INTERVAL_SECONDS,
    initialize_monitor,
    process_reading,
    read_source_rows,
)

logger = logging.getLogger("sensor_monitor")


def next_sample_number():
    """Get the next sample number without deleting existing history."""
    with sqlite3.connect(DB_PATH, timeout=10) as connection:
        result = connection.execute(
            "SELECT COALESCE(MAX(sample_number), 0) + 1 FROM readings"
        ).fetchone()
        return int(result[0])


def make_virtual_reading(source_row):
    """Create a new timestamped reading from the CSV pattern."""
    temperature = (
        source_row.get("temperature_C")
        or source_row.get("temperature_c")
        or source_row.get("accepted_value")
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_number": next_sample_number(),
        "sensor_name": "TMP36",
        "raw_value": source_row.get("raw_value"),
        "accepted_value": temperature,
        "status": source_row.get("status") or "OK",
    }


def main():
    initialize_monitor()
    rows = read_source_rows()

    if not rows:
        raise RuntimeError("Sensor CSV contains no readings")

    logger.info(
        "Virtual sensor worker started with %s source readings",
        len(rows),
    )

    while True:
        for source_row in rows:
            try:
                reading = make_virtual_reading(source_row)
                process_reading(reading)
            except Exception:
                logger.exception("Failed to process virtual sensor reading")

            time.sleep(SAMPLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Virtual sensor worker stopped by user")
