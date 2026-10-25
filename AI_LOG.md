
## Assignment 7.2 — Failure Investigation and Recovery Report

### AI assistance

ChatGPT was used to help organize the failure investigation report, identify the assignment requirements, improve documentation, and plan verification steps. AI-generated suggestions were reviewed against the existing code and logs.

### Failure scenario

The selected scenario was unexpected termination of the sensor worker. Existing evidence in `evidence/recovery_test.txt` and `logs/supervisor.log` documents a worker exit with code `-9` and subsequent restart activity.

### Verification

The project's automated tests were run using:

```bash
python -m pytest -q
```

Latest verified result: **[replace with the actual output from the final test run]**.

### Limitations

The worker exit code does not establish the original cause of termination. The report distinguishes observed evidence from possible explanations. Any additional tests and logging changes are documented only after they have been implemented and verified.

### Changes made

- Added or updated `failure_report.md`.
- Updated the README with the failure scenario and evidence locations.
- [Describe the actual logging improvement, if implemented.]
- [List the additional tests and their actual results.]
