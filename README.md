# EGN321 Module 8.2 — Sensor Monitoring and Tank Volume Capstone

## Project Overview

This project combines a virtual temperature sensor monitoring system with a rectangular tank volume calculator. It uses Python, Flask, and SQLite to process sensor readings, monitor system health, record alerts, and provide web-based tools.

The project also preserves and audits the original tank-fill workbook. Potential data and formula issues are documented rather than silently corrected.

## Main Features

### Sensor Monitoring

- Replays virtual sensor readings from a CSV file.
- Stores readings and monitoring state in SQLite.
- Displays recent readings, historical data, alerts, and health information.
- Detects stale sensor input.
- Activates and clears high-temperature alerts.
- Uses a supervisor to restart the sensor worker after unexpected exits.
- Provides a JSON health endpoint at `/health`.

### Tank Volume Calculator

The Flask page at `/tank-volume` calculates rectangular tank volume in US gallons.

Inputs:
- Length in feet
- Width in feet
- Depth
- Explicit depth unit: inches or feet

The calculation uses:

`Volume (gallons) = length (ft) × width (ft) × depth (ft) × 7.48052`

When depth is entered in inches, it is converted to feet by dividing by 12.

The calculator validates dimensions and requires an explicitly supported depth unit. Invalid input produces an error rather than a volume result.

### Workbook Audit

The original workbook is preserved at `original/TANK_FILL_rev4.xlsx`. Audit findings are documented in `evidence/workbook_audit.md`.

The audit identified an unresolved unit discrepancy for R-108:
- The `Tank Fill` sheet records a depth of `2.5` under a column labeled in inches.
- The `Field Notes` sheet records `2.5 ft`.

The correct unit must be verified before using that value for operational calculations. The workbook's total formula also appears to include R-101 through R-112 while omitting R-113 through R-118. The original workbook has not been modified.

## Requirements

- Python 3
- Flask
- pandas
- matplotlib
- pytest

Install dependencies in the project's virtual environment:

```bash
python -m pip install -r requirements.txt
```

## How to Run

Activate the project's virtual environment and open two terminals in the project directory.

**Terminal 1 — Web application**

```bash
python -u app.py
```

Open the sensor dashboard at:

http://127.0.0.1:5000/

Open the tank calculator at:

http://127.0.0.1:5000/tank-volume

Check the health endpoint at:

http://127.0.0.1:5000/health

**Terminal 2 — Sensor worker and recovery supervisor**

```bash
python -u supervisor.py
```

The supervisor launches `run_monitor.py`, which replays virtual sensor data and records readings in SQLite.

Stop the supervisor with `Control + C` when finished.

## Data and Project Files

- `data/sensor_readings.csv` — virtual sensor input
- `sensor_history.db` — SQLite monitoring database
- `monitor.py` — monitoring, database, health, and alert logic
- `history_builder.py` — historical data utilities
- `run_monitor.py` — sensor worker entry point
- `supervisor.py` — worker monitoring and restart logic
- `app.py` — Flask dashboard, health endpoint, and tank calculator route
- `tank_volume.py` — validated tank volume calculation
- `templates/dashboard.html` — sensor dashboard
- `templates/tank_volume.html` — tank calculator page
- `original/TANK_FILL_rev4.xlsx` — preserved source workbook
- `evidence/workbook_audit.md` — workbook audit findings
- `logs/application.log` — monitoring and application events
- `logs/supervisor.log` — worker lifecycle and recovery events
- `AI_LOG.md` — AI assistance and verification record

## Monitoring Behavior

The virtual sensor replay uses a sampling interval of 2 seconds. Input is considered stale when the most recent received reading is more than 8 seconds old.

High-temperature alert settings:
- Activation threshold: 28.0°C
- Activation: 3 consecutive accepted readings at or above the threshold
- Clearing threshold: below 27.0°C

The different activation and clearing thresholds provide hysteresis to reduce repeated alert changes near the threshold.

Health states and recovery behavior should be verified against the current health response, database records, and logs. A single successful health check does not prove every failure scenario has been tested.

## Testing

Run the automated test suite from the project directory:

```bash
python -m pytest -q
```

The current test suite has passed 21 tests. Coverage includes the existing monitoring, history, alert, and supervisor behavior, plus tank volume calculations and validation.

The Flask tank calculator route was also checked for:
- Successful page loading
- A valid volume calculation
- Rejection of invalid dimensions

Rerun the tests after future changes and use the actual output when recording results.

## Known Limitations

- Sensor readings are simulated from a CSV file; no physical sensor is connected.
- The tank calculator handles rectangular tank dimensions only.
- The R-108 depth unit discrepancy remains unresolved and requires verification.
- The original workbook's total formula may omit six tank runs.
- The supervisor restarts the worker while the supervisor itself is running. Operating-system startup after reboot is not configured by this script alone.
- Production use would require additional deployment, monitoring, and operational validation.

## Evidence

The `evidence/` directory contains records and screenshots from prior monitoring and recovery work, along with the workbook audit. Review each evidence file to confirm what it demonstrates and whether it reflects the current capstone state.

## AI Usage Disclosure

See `AI_LOG.md` for documentation of AI assistance and local verification.
