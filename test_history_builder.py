import sqlite3

from history_builder import (
    connect_database,
    detect_gaps,
    log_readings,
)


def test_database_logging(tmp_path):
    """A logged reading can be retrieved with its fields intact."""
    db_path = tmp_path / "test_history.db"

    reading = {
        "timestamp": "2026-10-10T12:00:00",
        "sample_number": 1,
        "sensor_name": "TMP36",
        "raw_value": 151,
        "accepted_value": 23.80,
        "status": "OK",
    }

    connection = connect_database(db_path)
    try:
        count = log_readings(connection, [reading])
        saved = connection.execute("""
            SELECT timestamp, sample_number, sensor_name,
                   raw_value, accepted_value, status
            FROM readings
        """).fetchone()

        assert count == 1
        assert saved == (
            "2026-10-10T12:00:00",
            1,
            "TMP36",
            151.0,
            23.8,
            "OK",
        )
    finally:
        connection.close()


def test_gap_detection_identifies_missing_sample():
    """A two-second interval reveals one missing one-second slot."""
    readings = [
        {
            "timestamp": "2026-10-10T12:00:00",
            "sample_number": 1,
        },
        {
            "timestamp": "2026-10-10T12:00:02",
            "sample_number": 3,
        },
    ]

    gaps = detect_gaps(readings, interval_seconds=1)

    assert len(gaps) == 1
    assert gaps[0]["elapsed_seconds"] == 2
    assert gaps[0]["missing_readings"] == 1


def test_consecutive_samples_have_no_gap():
    readings = [
        {
            "timestamp": "2026-10-10T12:00:00",
            "sample_number": 1,
        },
        {
            "timestamp": "2026-10-10T12:00:01",
            "sample_number": 2,
        },
    ]

    assert detect_gaps(readings, interval_seconds=1) == []
