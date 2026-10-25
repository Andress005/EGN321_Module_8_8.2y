import sqlite3
import tempfile
from pathlib import Path

import monitor


def main():
    # Preserve the real database and test against a temporary copy.
    original_db = monitor.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        monitor.DB_PATH = Path(temp_dir) / "test_sensor.db"

        try:
            monitor.initialize_monitor()

            with monitor.connect_database() as connection:
                connection.execute(
                    """
                    CREATE TABLE readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        sample_number INTEGER NOT NULL UNIQUE,
                        sensor_name TEXT NOT NULL,
                        raw_value REAL,
                        accepted_value REAL,
                        status TEXT NOT NULL
                    )
                    """
                )
                connection.commit()

            # Three consecutive high readings should activate the alert.
            for value in (28.2, 28.5, 29.0):
                with monitor.connect_database() as connection:
                    monitor.update_alert(connection, value)
                    connection.commit()

            with monitor.connect_database() as connection:
                active = connection.execute(
                    "SELECT status, peak_value_c FROM alerts "
                    "ORDER BY id DESC LIMIT 1"
                ).fetchone()

            assert active is not None, "Alert did not activate"
            assert active[0] == "ACTIVE", f"Unexpected alert: {active}"
            assert active[1] == 29.0, f"Unexpected peak: {active}"

            print("PASS: Alert activated after 3 consecutive high readings.")

            # A reading below the clear threshold should clear the alert.
            with monitor.connect_database() as connection:
                monitor.update_alert(connection, 26.5)
                connection.commit()

            with monitor.connect_database() as connection:
                cleared = connection.execute(
                    "SELECT status, cleared_at FROM alerts "
                    "ORDER BY id DESC LIMIT 1"
                ).fetchone()

            assert cleared[0] == "CLEARED", f"Alert did not clear: {cleared}"
            assert cleared[1] is not None, "Clear timestamp missing"

            print("PASS: Alert cleared below 27°C.")
            print("PASS: Alert test completed successfully.")

        finally:
            monitor.DB_PATH = original_db


def test_alert_activation_and_recovery():
    main()


if __name__ == "__main__":
    main()