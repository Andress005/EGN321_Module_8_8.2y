import csv
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "sensor_readings.csv"
DB_PATH = BASE_DIR / "sensor_history.db"
OUTPUT_DIR = BASE_DIR / "reports"

SENSOR_NAME = "TMP36"
EXPECTED_INTERVAL_SECONDS = 1

# Classroom replay timestamp, not an original sensor timestamp.
REPLAY_START = datetime.fromisoformat("2026-10-10T12:00:00")


def connect_database(db_path=DB_PATH):
    """Create the SQLite database and readings table."""
    connection = sqlite3.connect(db_path)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sample_number INTEGER NOT NULL UNIQUE,
            sensor_name TEXT NOT NULL,
            raw_value REAL,
            accepted_value REAL,
            status TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_timestamp
        ON readings(timestamp)
    """)
    connection.commit()
    return connection


def load_csv(csv_path=CSV_PATH):
    """Read source data without modifying the original CSV."""
    readings = []

    with open(csv_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = {"sample", "raw_value", "temperature_C", "status"}

        if not required.issubset(reader.fieldnames or []):
            raise ValueError(
                f"CSV must contain these columns: {sorted(required)}"
            )

        for row in reader:
            sample_number = int(row["sample"])
            status = row["status"].strip()
            raw_text = row["raw_value"].strip()
            temperature_text = row["temperature_C"].strip()

            raw_value = float(raw_text) if raw_text else None
            temperature = float(temperature_text) if temperature_text else None
            # Reconstruct timestamps from the sample sequence.
            timestamp = REPLAY_START + timedelta(
                seconds=(sample_number - 1) * EXPECTED_INTERVAL_SECONDS
            )

            # Only readings marked OK are accepted for analysis.
            accepted_value = (
                temperature
                if status == "OK" and temperature is not None
                else None
            )

            readings.append({
                "timestamp": timestamp.isoformat(timespec="seconds"),
                "sample_number": sample_number,
                "sensor_name": SENSOR_NAME,
                "raw_value": raw_value,
                "accepted_value": accepted_value,
                "status": status,
            })

    if not readings:
        raise ValueError("The CSV contains no readings.")

    return readings


def log_readings(connection, readings):
    """Replace imported rows with the current source dataset."""
    connection.execute("DELETE FROM readings")

    connection.executemany("""
        INSERT INTO readings (
            timestamp, sample_number, sensor_name,
            raw_value, accepted_value, status
        ) VALUES (
            :timestamp, :sample_number, :sensor_name,
            :raw_value, :accepted_value, :status
        )
    """, readings)

    connection.commit()
    return len(readings)


def fetch_all(connection):
    connection.row_factory = sqlite3.Row
    return connection.execute("""
        SELECT timestamp, sample_number, sensor_name,
               raw_value, accepted_value, status
        FROM readings
        ORDER BY timestamp, sample_number
    """).fetchall()


def query_window(connection, duration):
    """Query a window relative to the latest timestamp in the database."""
    latest = connection.execute(
        "SELECT MAX(timestamp) FROM readings"
    ).fetchone()[0]

    if latest is None:
        return []

    latest_time = datetime.fromisoformat(latest)
    cutoff = (latest_time - duration).isoformat(timespec="seconds")

    connection.row_factory = sqlite3.Row
    return connection.execute("""
        SELECT timestamp, sample_number, sensor_name,
               raw_value, accepted_value, status
        FROM readings
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp, sample_number
    """, (cutoff, latest)).fetchall()


def detect_gaps(readings, interval_seconds=EXPECTED_INTERVAL_SECONDS):
    """Find absent samples or timestamp intervals between stored rows."""
    ordered = sorted(
        readings,
        key=lambda row: (
            row["sample_number"],
            row["timestamp"]
        )
    )
    gaps = []

    for previous, current in zip(ordered, ordered[1:]):
        previous_time = datetime.fromisoformat(previous["timestamp"])
        current_time = datetime.fromisoformat(current["timestamp"])

        elapsed = (current_time - previous_time).total_seconds()
        sample_difference = (
            current["sample_number"] - previous["sample_number"]
        )

        # A gap exists if either timestamps or sample sequence show one.
        missing_by_time = max(
            0, round(elapsed / interval_seconds) - 1
        )
        missing_by_sample = max(0, sample_difference - 1)
        missing_count = max(missing_by_time, missing_by_sample)

        if elapsed > interval_seconds or sample_difference > 1:
            gaps.append({
                "start": previous["timestamp"],
                "end": current["timestamp"],
                "elapsed_seconds": elapsed,
                "missing_readings": missing_count,
            })

    return gaps


def summarize(readings):
    statuses = Counter(row["status"] for row in readings)
    values = [
        float(row["accepted_value"])
        for row in readings
        if row["accepted_value"] is not None
    ]

    values.sort()
    median = None
    if values:
        middle = len(values) // 2
        if len(values) % 2:
            median = values[middle]
        else:
            median = (values[middle - 1] + values[middle]) / 2

    return {
        "count": len(readings),
        "statuses": statuses,
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "median": median,
        "gaps": detect_gaps(readings),
    }


def format_value(value):
    return "N/A" if value is None else f"{value:.2f} °C"


def write_window_report(path, title, readings):
    summary = summarize(readings)
    lines = [
        title,
        "=" * len(title),
        f"Record count: {summary['count']}",
        f"Status counts: {dict(summary['statuses'])}",
        f"Minimum accepted temperature: {format_value(summary['minimum'])}",
        f"Maximum accepted temperature: {format_value(summary['maximum'])}",
        f"Median accepted temperature: {format_value(summary['median'])}",
        f"Detected time gaps: {len(summary['gaps'])}",
    ]

    for gap in summary["gaps"]:
        lines.append(
            f"  {gap['start']} to {gap['end']}: "
            f"{gap['elapsed_seconds']} seconds elapsed; "
            f"estimated absent slots: {gap['missing_readings']}"
        )

    if not summary["gaps"]:
        lines.append("No time gaps detected in this window.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_full_report(path, readings):
    summary = summarize(readings)

    if readings:
        first_sample = min(row["sample_number"] for row in readings)
        last_sample = max(row["sample_number"] for row in readings)
        expected = last_sample - first_sample + 1
    else:
        expected = 0

    missing = max(0, expected - len(readings))
    completeness = 100 * len(readings) / expected if expected else 0

    largest_gap = max(
        summary["gaps"],
        key=lambda gap: gap["elapsed_seconds"],
        default=None,
    )

    lines = [
        "Full-History Report",
        "===================",
        f"Total records: {len(readings)}",
        f"Expected sample slots in observed sample-number range: {expected}",
        f"Missing sample slots: {missing}",
        f"Completeness: {completeness:.2f}%",
        f"Status counts: {dict(summary['statuses'])}",
        f"Detected time gaps: {len(summary['gaps'])}",
    ]

    if largest_gap:
        lines.append(
            f"Largest detected gap: {largest_gap['elapsed_seconds']} seconds "
            f"({largest_gap['start']} to {largest_gap['end']})"
        )
    else:
        lines.append("Largest detected gap: none detected")

    lines.extend([
        "",
        "Timestamp method: reconstructed classroom replay timestamps.",
        "Replay start: " + REPLAY_START.isoformat(timespec="seconds"),
        f"Expected interval: {EXPECTED_INTERVAL_SECONDS} second(s).",
        "Completeness is based on sample-number slots, not proof of actual "
        "wall-clock sensor uptime.",
        "A MISSING_SIMULATED status is not itself a missing timestamp.",
    ])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_plot(readings, output_path):
    """Plot accepted values and break lines across detected gaps."""
    ordered = sorted(readings, key=lambda row: row["sample_number"])
    times = []
    values = []

    previous_time = None
    for row in ordered:
        current_time = datetime.fromisoformat(row["timestamp"])

        if previous_time is not None:
            elapsed = (current_time - previous_time).total_seconds()
            if elapsed > EXPECTED_INTERVAL_SECONDS:
                # NaN breaks the plotted line rather than connecting a gap.
                times.append(current_time)
                values.append(float("nan"))

        times.append(current_time)
        values.append(
            float(row["accepted_value"])
            if row["accepted_value"] is not None
            else float("nan")
        )
        previous_time = current_time

    plt.figure(figsize=(11, 5))
    plt.plot(times, values, marker=".", linewidth=1)
    plt.title("TMP36 Temperature History — Reconstructed Timestamps")
    plt.xlabel("Reconstructed replay time")
    plt.ylabel("Accepted temperature (°C)")
    plt.grid(True, alpha=0.3)
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def run_pipeline():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    readings = load_csv()

    with connect_database() as connection:
        log_readings(connection, readings)
        stored = fetch_all(connection)

        last_hour = query_window(connection, timedelta(hours=1))
        last_day = query_window(connection, timedelta(days=1))

        write_window_report(
            OUTPUT_DIR / "last_hour_report.txt",
            "Last-Hour Report",
            last_hour,
        )
        write_window_report(
            OUTPUT_DIR / "last_day_report.txt",
            "Last-Day Report",
            last_day,
        )
        write_full_report(
            OUTPUT_DIR / "full_history_report.txt",
            stored,
        )
        create_plot(stored, OUTPUT_DIR / "history_plot.png")

    print(f"Imported {len(readings)} readings into {DB_PATH.name}")
    print(f"Reports and plot saved in: {OUTPUT_DIR}")
    print(f"Last hour: {len(last_hour)} records")
    print(f"Last day: {len(last_day)} records")
    print(f"Full history: {len(stored)} records")


if __name__ == "__main__":
    run_pipeline()
