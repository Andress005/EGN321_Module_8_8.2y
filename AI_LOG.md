# EGN321 Module 8.2 — AI Usage and Verification Log

## AI assistance

ChatGPT was used to help organize the capstone work, review the legacy tank-fill workbook, plan the tank-volume calculation, implement input validation, integrate the calculator into the Flask application, and update project documentation.

AI-generated suggestions were applied and checked through local commands and automated tests. The original workbook was preserved rather than edited.

## Work completed

- Set up the capstone repository using the existing sensor-monitoring project as the baseline.
- Reviewed the legacy workbook and documented the R-108 depth-unit discrepancy and the apparent total-formula range issue in `evidence/workbook_audit.md`.
- Preserved the original workbook at `original/TANK_FILL_rev4.xlsx`.
- Added `tank_volume.py` to calculate rectangular tank volume in US gallons, with explicit depth units and input validation.
- Added `test_tank_volume.py` for calculation and validation tests.
- Added the Flask `/tank-volume` route and `templates/tank_volume.html`.
- Updated `README.md` to document the capstone features, setup, execution, testing, and known limitations.

## Verification performed

The automated test suite was run with:

```bash
python -m pytest -q
```

Verified result during calculator development:

**21 passed in 0.26s**

The Flask test client was also used to verify:
- `GET /tank-volume` returned HTTP 200.
- A calculation using length 10 ft, width 5 ft, and depth 12 in returned the expected 374.03 US gallons.
- Invalid negative dimensions displayed a validation error.

The 21-test result includes the existing monitoring tests and the new tank-volume tests.

## Existing monitoring and recovery evidence

The project contains earlier sensor-worker recovery evidence in `evidence/recovery_test.txt` and `logs/supervisor.log`. That evidence documents prior worker termination and restart activity.

The current capstone changes did not independently repeat every sensor recovery scenario. Earlier recovery records are retained as existing evidence and should not be interpreted as a new recovery test performed during the tank-calculator work.

## Known limitations

- The sensor input is simulated from CSV data rather than a physical sensor.
- The tank calculator supports rectangular tank dimensions only.
- The correct unit for the R-108 depth must be verified against the original source before operational use.
- The apparent workbook total-formula range issue requires review before relying on the workbook total.
- A worker exit code alone does not establish the original cause of termination.

## Final verification record

The test result above was observed during development. Rerun the test suite before final submission and update this log if the final result differs.
