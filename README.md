# EGN321 Module 7.1 — Unattended Sensor Monitoring System

## Project Overview

This project implements a virtual temperature sensor monitoring system using Python, Flask, and SQLite. It monitors replayed sensor data, records readings, detects stale input, generates temperature alerts, and provides a web dashboard for system health and history.

## System Architecture

Virtual sensor CSV replay → Reading validation and processing → SQLite history → Threshold alert logic → Flask dashboard and application logs.

A Python supervisor monitors the sensor worker and restarts it if the worker exits unexpectedly.

## Requirements

- Python 3
- Flask
- pandas
- matplotlib
- pytest

Install dependencies in the project virtual environment:

```bash
python -m pip install -r requirements.txt
```

## How to Run

Open two terminals in the project directory and activate the virtual environment in each.

**Terminal 1 — Dashboard**

```bash
python -u app.py
```

Open http://127.0.0.1:5000 in your browser.

**Terminal 2 — Sensor worker and recovery supervisor**

```bash
python -u supervisor.py
```

The supervisor launches `run_monitor.py`, which continuously replays the virtual sensor CSV and records readings in SQLite.

Stop the supervisor with `Control + C` when finished.

## Data Storage

- `data/sensor_readings.csv` — virtual sensor input
- `sensor_history.db` — persistent SQLite database
- `history_builder.py` — historical data and reporting utilities
- `logs/application.log` — application events, readings, and alert events
- `logs/supervisor.log` — worker startup, termination, and recovery events

The monitoring worker appends readings to the existing database rather than replacing the historical records.

## Sampling and Stale-Data Detection

The virtual sensor replay uses a sampling interval of 2 seconds. Input is considered stale when the most recent received reading is more than 8 seconds old.

Stale input is marked as degraded, and stale values should not be presented as current readings. Missing or rejected input should not be silently represented as a valid measurement.

## Temperature Alert Logic

- High-temperature threshold: 28.0°C
- Activation: 3 consecutive accepted readings at or above the threshold
- Clearing: an accepted reading below 27.0°C
- Hysteresis: the different activation and clearing thresholds reduce repeated alert changes near the threshold

Alert activation and clearing events are recorded in the application log and stored in the SQLite `alerts` table.

## Health States

- **HEALTHY:** recent input is being processed normally.
- **DEGRADED:** input is stale or unavailable.
- **FAILED:** a fatal monitoring failure has occurred; inspect the logs to diagnose the issue.
- **RECOVERING:** the supervisor is restarting the sensor worker after it exits.

The dashboard exposes a health endpoint at `/health`.

## Automatic Worker Recovery

Run `supervisor.py` to keep the virtual sensor worker under supervision. If the worker exits unexpectedly, the supervisor records the exit code, waits 3 seconds, and starts the worker again.

This recovery mechanism operates while the supervisor itself is running. Automatic startup after a computer reboot or login is not configured by this Python supervisor alone.


## Testing

Run the automated tests from the project directory:

```bash
python -m pytest -q
```

The current test suite passes 7 tests. The tests cover existing history and alert behavior, along with supervisor failure logging for worker exit codes -9, 1, and 0.

The supervisor logging improvement records the worker PID, exit code, and restart delay when a worker stops. This information helps distinguish which process stopped and what recovery action was scheduled.

Existing recovery evidence in `evidence/recovery_test.txt` documents a worker being forcibly terminated, the supervisor detecting exit code -9, and a replacement worker being launched. This existing record is separate from the automated logging tests.

After recovery, verify the dashboard, `/health` endpoint, SQLite history, and alert behavior. A passing logging test alone does not establish that every part of the recovery process works.

## Limitations

This is a simulated sensor system that replays CSV data; it is not connected to a physical sensor. Recovery is demonstrated for the sensor worker while the supervisor is running. A production deployment would require an operating-system process manager, additional monitoring, and appropriate service configuration for automatic startup after reboot.

## Evidence

The `evidence/` directory should contain screenshots or test records demonstrating:

- Dashboard and latest reading
- Historical readings and health state
- Alert activation and clearing
- Stale-input detection
- Application logs
- Worker interruption and supervisor recovery
- Final healthy state

## AI Usage Disclosure

See `AI_LOG.md` for a record of AI assistance and local verification.


## Assignment 7.2: Failure Investigation and Recovery

### Failure scenario

The investigation uses unexpected termination of the sensor worker while the supervisor is running. The supervisor is responsible for detecting the worker exit and attempting to restart it.

### Evidence files

- `failure_report.md` — the 13-section failure investigation and recovery report.
- `logs/supervisor.log` — supervisor startup, worker lifecycle, and restart events.
- `logs/application.log` — application and sensor-monitoring events.
- `evidence/recovery_test.txt` — existing worker-termination and recovery evidence.
- `evidence/` — screenshots and additional verification output.

### Run automated tests

Activate the project's virtual environment and run:

```bash
python -m pytest -q
```

Record the actual test result in the report and AI log.

### Check system health

When the Flask application is running on port 5050, use:

```bash
curl -i http://127.0.0.1:5050/health
```

The health response should be inspected for the health state, latest reading, and stale-data flag. A healthy response at one point in time does not by itself prove that every failure-recovery scenario has been tested.

### Recovery design

The supervisor monitors the sensor worker and attempts to restart it when it exits. SQLite history and logs are retained to support investigation rather than being deleted to hide the failure.

### Known limitations

A worker exit code does not necessarily identify the underlying cause. Recovery should be verified using sensor readings, database access, dashboard availability, alert behavior, and system health.
