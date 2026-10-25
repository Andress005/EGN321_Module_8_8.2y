
from datetime import datetime, timezone

from flask import Flask, render_template, request

from tank_volume import calculate_volume_gallons

from monitor import (
    DB_PATH,
    HIGH_THRESHOLD_C,
    STALE_AFTER_SECONDS,
    connect_database,
    get_health,
)

app = Flask(__name__)


def load_dashboard_data():
    connection = connect_database()
    try:
        latest = connection.execute(
            """
            SELECT timestamp, sample_number, accepted_value, status
            FROM readings
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        history = connection.execute(
            """
            SELECT timestamp, sample_number, accepted_value, status
            FROM readings
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

        alerts = connection.execute(
            """
            SELECT activated_at, cleared_at, threshold_c,
                   peak_value_c, status
            FROM alerts
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()

        last_received = connection.execute(
            "SELECT value FROM monitor_state WHERE key = 'last_received_at'"
        ).fetchone()

        latest_received_at = last_received["value"] if last_received else None

        age_seconds = None
        if latest_received_at:
            received_time = datetime.fromisoformat(latest_received_at)
            age_seconds = (
                datetime.now(timezone.utc) - received_time
            ).total_seconds()

        is_stale = age_seconds is None or age_seconds > STALE_AFTER_SECONDS

        return {
            "latest": dict(latest) if latest else None,
            "history": [dict(row) for row in history],
            "alerts": [dict(row) for row in alerts],
            "health": get_health(),
            "age_seconds": age_seconds,
            "is_stale": is_stale,
            "threshold": HIGH_THRESHOLD_C,
            "database": str(DB_PATH.name),
        }
    finally:
        connection.close()


@app.route("/")
def dashboard():
    data = load_dashboard_data()
    return render_template("dashboard.html", **data)


@app.route("/health")
def health():
    data = load_dashboard_data()
    return {
        "health": data["health"],
        "stale": data["is_stale"],
        "latest_reading": data["latest"],
    }


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)


@app.route("/tank-volume", methods=["GET", "POST"])
def tank_volume():
    result = None
    error = None

    values = {
        "length_ft": "",
        "width_ft": "",
        "depth": "",
        "depth_unit": "in",
    }

    if request.method == "POST":
        values = {
            "length_ft": request.form.get("length_ft", "").strip(),
            "width_ft": request.form.get("width_ft", "").strip(),
            "depth": request.form.get("depth", "").strip(),
            "depth_unit": request.form.get("depth_unit", "in"),
        }

        try:
            result = calculate_volume_gallons(
                values["length_ft"],
                values["width_ft"],
                values["depth"],
                values["depth_unit"],
            )
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "tank_volume.html",
        result=result,
        error=error,
        values=values,
    )
