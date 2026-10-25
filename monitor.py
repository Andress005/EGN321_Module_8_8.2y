
import csv
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "sensor_history.db"
CSV_PATH = BASE_DIR / "data" / "sensor_readings.csv"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "application.log"

SAMPLE_INTERVAL_SECONDS = 2
STALE_AFTER_SECONDS = 8
FAILED_AFTER_SECONDS = 30

HIGH_THRESHOLD_C = 28.0
CLEAR_THRESHOLD_C = 27.0
CONSECUTIVE_READINGS_REQUIRED = 3

LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sensor_monitor")


def utc_now():
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def connect_database():
    """Connect to the existing database and ensure monitor tables exist."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activated_at TEXT NOT NULL,
            cleared_at TEXT,
            threshold_c REAL NOT NULL,
            peak_value_c REAL NOT NULL,
            status TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS monitor_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def set_state(connection, key, value):
    """Insert or update a monitor state value."""
    connection.execute(
        """
        INSERT INTO monitor_state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, str(value)),
    )


def get_state(connection, key, default=None):
    """Retrieve a monitor state value."""
    row = connection.execute(
        "SELECT value FROM monitor_state WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def initialize_monitor():
    """Initialize monitoring tables without deleting existing history."""
    connection = connect_database()
    try:
        set_state(connection, "health", "HEALTHY")
        if get_state(connection, "consecutive_high") is None:
            set_state(connection, "consecutive_high", "0")
        connection.commit()
        logger.info("Monitoring service initialized; existing history preserved")
    finally:
        connection.close()


def read_source_rows():
    """Read sensor readings from the configured CSV file."""
    if not CSV_PATH.exists():
        logger.error("Sensor source file not found: %s", CSV_PATH)
        return []

    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return list(reader)


def parse_reading(row):
    """Extract common reading fields from CSV rows."""
    timestamp = (
        row.get("timestamp")
        or row.get("Timestamp")
        or row.get("datetime")
        or utc_now()
    )

    sample_number = (
        row.get("sample_number")
        or row.get("sample")
        or row.get("reading_id")
        or row.get("id")
    )

    sensor_name = (
        row.get("sensor_name")
        or row.get("sensor")
        or row.get("Sensor")
        or "TMP36"
    )

    raw_value = (
        row.get("raw_value")
        or row.get("measured_temp_c")
        or row.get("temperature_c")
        or row.get("temperature")
        or row.get("value")
        or row.get("raw")
    )

    accepted_value = (
        row.get("accepted_value")
        or row.get("accepted_temp_c")
        or row.get("predicted_temp_c")
        or raw_value
    )

    status = row.get("status") or row.get("status_reason") or "OK"

    try:
        raw_value = float(raw_value) if raw_value not in (None, "") else None
    except (ValueError, TypeError):
        raw_value = None

    try:
        accepted_value = (
            float(accepted_value)
            if accepted_value not in (None, "")
            else None
        )
    except (ValueError, TypeError):
        accepted_value = None

    if accepted_value is None or raw_value is None:
        status = "REJECTED"

    if sample_number in (None, ""):
        sample_number = int(time.time() * 1000)
    else:
        try:
            sample_number = int(float(sample_number))
        except (ValueError, TypeError):
            sample_number = int(time.time() * 1000)

    return {
        "timestamp": str(timestamp),
        "sample_number": sample_number,
        "sensor_name": str(sensor_name),
        "raw_value": raw_value,
        "accepted_value": accepted_value,
        "status": str(status),
    }


def update_alert(connection, value):
    """Activate after consecutive high readings and clear below threshold."""
    count = int(get_state(connection, "consecutive_high", "0") or "0")

    if value is None:
        set_state(connection, "consecutive_high", "0")
        return

    active = connection.execute(
        "SELECT id, peak_value_c FROM alerts "
        "WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if value >= HIGH_THRESHOLD_C:
        count += 1
        set_state(connection, "consecutive_high", str(count))

        if active:
            if value > active["peak_value_c"]:
                connection.execute(
                    "UPDATE alerts SET peak_value_c = ? WHERE id = ?",
                    (value, active["id"]),
                )
        elif count >= CONSECUTIVE_READINGS_REQUIRED:
            cursor = connection.execute(
                """
                INSERT INTO alerts (
                    activated_at, cleared_at, threshold_c,
                    peak_value_c, status
                )
                VALUES (?, NULL, ?, ?, 'ACTIVE')
                """,
                (utc_now(), HIGH_THRESHOLD_C, value),
            )
            set_state(connection, "consecutive_high", "0")
            logger.warning(
                "ALERT ACTIVATED id=%s value=%.2fC threshold=%.2fC",
                cursor.lastrowid,
                value,
                HIGH_THRESHOLD_C,
            )
    else:
        set_state(connection, "consecutive_high", "0")

        if active and value < CLEAR_THRESHOLD_C:
            connection.execute(
                "UPDATE alerts SET status = 'CLEARED', cleared_at = ? "
                "WHERE id = ?",
                (utc_now(), active["id"]),
            )
            logger.info(
                "ALERT CLEARED id=%s value=%.2fC",
                active["id"],
                value,
            )


def process_reading(row):
    """Validate, persist, and evaluate one reading."""
    reading = parse_reading(row)
    connection = connect_database()

    try:
        existing = connection.execute(
            "SELECT 1 FROM readings WHERE sample_number = ?",
            (reading["sample_number"],),
        ).fetchone()

        if existing:
            logger.warning(
                "Duplicate sample skipped: %s",
                reading["sample_number"],
            )
            return False

        connection.execute(
            """
            INSERT INTO readings (
                timestamp, sample_number, sensor_name,
                raw_value, accepted_value, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                reading["timestamp"],
                reading["sample_number"],
                reading["sensor_name"],
                reading["raw_value"],
                reading["accepted_value"],
                reading["status"],
            ),
        )

        received_at = utc_now()
        set_state(connection, "last_received_at", received_at)
        set_state(connection, "health", "HEALTHY")

        if reading["status"].upper() in ("OK", "ACCEPTED", "VALID"):
            update_alert(connection, reading["accepted_value"])
        else:
            set_state(connection, "consecutive_high", "0")
            logger.warning(
                "Rejected reading sample=%s status=%s",
                reading["sample_number"],
                reading["status"],
            )

        connection.commit()
        logger.info(
            "Reading stored sample=%s value=%s status=%s",
            reading["sample_number"],
            reading["accepted_value"],
            reading["status"],
        )
        return True

    except sqlite3.Error:
        connection.rollback()
        logger.exception("Database error while processing reading")
        raise
    finally:
        connection.close()


def get_health():
    """Determine health from the time elapsed since the last reading."""
    connection = connect_database()

    try:
        last_received = get_state(connection, "last_received_at", "")

        if not last_received:
            return "FAILED"

        try:
            received_at = datetime.fromisoformat(last_received)
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            logger.exception("Invalid last_received_at timestamp")
            return "FAILED"

        age = (datetime.now(timezone.utc) - received_at).total_seconds()

        if age > FAILED_AFTER_SECONDS:
            health = "FAILED"
        elif age > STALE_AFTER_SECONDS:
            health = "DEGRADED"
        else:
            health = "HEALTHY"

        previous_health = get_state(connection, "health", "")
        if health != previous_health:
            set_state(connection, "health", health)
            connection.commit()

            if health == "FAILED":
                logger.error(
                    "Health state changed to FAILED; input age=%.1fs", age
                )
            elif health == "DEGRADED":
                logger.warning(
                    "Health state changed to DEGRADED; input age=%.1fs", age
                )
            else:
                logger.info("Health state changed to HEALTHY")

        return health
    finally:
        connection.close()


def run_monitor(stop_event=None):
    """Replay CSV readings at a fixed interval until stopped or exhausted."""
    initialize_monitor()
    logger.info("Monitoring loop started")

    try:
        rows = read_source_rows()
        if not rows:
            logger.error("Sensor source contains no readings")
            return

        for row in rows:
            if stop_event is not None and stop_event.is_set():
                break

            process_reading(row)

            if stop_event is not None:
                if stop_event.wait(SAMPLE_INTERVAL_SECONDS):
                    break
            else:
                time.sleep(SAMPLE_INTERVAL_SECONDS)

        logger.info("Monitoring source replay completed")

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception:
        logger.exception("Monitoring worker encountered an error")
        raise


if __name__ == "__main__":
    run_monitor()
