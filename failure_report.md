
# EGN321 Module 7.2 — Failure Investigation and Recovery Report

## 1. System Before Failure

The system uses a virtual temperature sensor that replays CSV readings. Python processes and validates the readings, SQLite stores historical data, alert logic detects high temperatures, and a Flask application provides the dashboard and health endpoint.

The supervisor launches the sensor worker and monitors its process. If the worker exits, the supervisor logs the exit code, waits three seconds, and attempts to launch a replacement.

The project includes `run_monitor.py`, `monitor.py`, `history_builder.py`, `app.py`, `supervisor.py`, a SQLite database, application logs, supervisor logs, and automated tests.

The October 15 recovery evidence documents that the dashboard and SQLite history remained usable during a worker-recovery test. A later health check on October 18 returned `HEALTHY`, a latest accepted reading of 25.76°C, and `stale: false`. The alert state before the October 15 failure was not recorded in the available evidence.

## 2. Failure Introduced

The selected failure was unexpected termination of the sensor worker while the supervisor was running.

According to `evidence/recovery_test.txt`, the worker was deliberately terminated using `kill -9`. This forcibly stops a process without allowing it to perform its normal shutdown procedure.

The supervisor log recorded the worker stopping with exit code `-9` at `2026-10-15 17:26:50.310`. The expected behavior was for the supervisor to detect the termination, wait three seconds, and launch a replacement worker. The log shows that a new worker started at `2026-10-15 17:26:53.325`.

This failure experiment was documented on October 15. The automated test run on October 18 was a separate activity.

## 3. First Observable Symptom

The first observable symptom in the supervisor log was a warning that the worker had stopped with exit code `-9`.

The warning showed that the worker had terminated and that a restart was scheduled. This was the first recorded indication of the failure in the available supervisor evidence. The log does not establish whether other symptoms occurred before this warning because a complete synchronized application and operating-system event timeline was not captured.

## 4. Log Evidence

The primary evidence is `logs/supervisor.log` and `evidence/recovery_test.txt`.

The October 15 supervisor log recorded:

- `17:24:55.948` — Supervisor started.
- `17:24:55.948` — Supervisor began starting the virtual sensor worker.
- `17:24:55.950` — Worker PID 68927 started.
- `17:26:50.310` — Worker stopped with exit code `-9`; restart scheduled after three seconds.
- `17:26:53.318` — Supervisor began starting a replacement worker.
- `17:26:53.325` — Replacement worker PID 68977 started.

The log demonstrates the worker lifecycle and restart sequence. The recovery evidence also records that the dashboard and SQLite history remained usable.

A separate sequence on October 15 shows repeated worker exits with code `1`, followed by restart attempts. Those entries demonstrate that the supervisor can repeatedly restart a worker, but they do not explain the cause of those exits.

### Evidence timeline table

| Time | Component | Event | Evidence | Interpretation |
|---|---|---|---|---|
| Oct 15, 17:24:55.948 | Supervisor | Supervisor starts | `supervisor.log` | Recovery monitoring begins |
| Oct 15, 17:24:55.950 | Worker | Worker starts | PID 68927 | Initial worker is running |
| Oct 15, 17:26:50.310 | Supervisor | Worker exit detected | Exit code `-9` | Worker terminated unexpectedly |
| Oct 15, 17:26:50.310 | Supervisor | Restart scheduled | Three-second delay in warning | Supervisor enters restart sequence |
| Oct 15, 17:26:53.318 | Supervisor | Replacement launch begins | `supervisor.log` | Recovery attempt proceeds |
| Oct 15, 17:26:53.325 | Worker | Replacement starts | PID 68977 | A new worker process is running |
| Oct 18, 14:18:16.908 | Worker | Worker starts | PID 5110 | Later supervisor session launches a worker |
| Oct 18, test run | Automated tests | Test suite passes | `evidence/pytest_results.txt` | Seven tests pass; this is not a new failure experiment |

## 5. Timeline of Events

The documented recovery experiment occurred on October 15, 2026.

1. The supervisor and worker were started.
2. The worker ran for approximately one minute and 54 seconds before its termination was detected.
3. The worker was forcibly terminated with `kill -9`.
4. The supervisor recorded exit code `-9` and scheduled a restart after three seconds.
5. The supervisor launched a replacement worker approximately three seconds later.
6. The existing recovery evidence records that the dashboard and SQLite history remained usable.
7. On October 18, the automated test suite completed with seven passing tests. The supervisor code was also improved to include the worker PID in its failure log messages.

The timestamps above come from the recorded logs. The exact command execution time for the termination was not separately recorded.

## 6. Possible Cause 1: External Process Termination

**Hypothesis:** The worker was forcibly terminated by an external action, such as a user or process-management command.

**Supporting evidence:** The recorded experiment explicitly states that `kill -9` was used. The supervisor recorded exit code `-9`, consistent with termination by signal 9 on Unix-like systems.

**Missing evidence:** The supervisor log does not identify who or what sent the signal. In a naturally occurring failure, the exit code alone would not establish the origin of the signal.

**Deterministic test:** Start the supervisor, identify its worker PID, terminate that worker with `kill -9 <PID>`, and inspect the supervisor log. The expected result is an exit code of `-9`, followed by a replacement worker with a different PID.

**Result:** The October 15 recovery evidence documents this experiment and shows the expected restart sequence.

## 7. Possible Cause 2: An Internal Worker Error

**Hypothesis:** The worker could exit because of an unhandled Python exception, an invalid runtime dependency, or another internal application error.

**Supporting evidence:** The supervisor log contains multiple worker exits with code `1` on October 15. This is consistent with an unsuccessful process exit, but it does not identify the underlying reason.

**Missing evidence:** The available supervisor entries do not include the worker's exception traceback, captured standard error, or a specific application error immediately preceding each exit. Exit code `1` alone does not prove that an unhandled exception occurred.

**Deterministic test:** In an isolated test environment, run a worker process with a controlled failure that raises an exception. Capture its standard error and exit code. Then verify that the supervisor records the worker's exit and starts a replacement. The test should use a temporary test worker and must not alter the production project database.

**Result:** The existing logs establish that exits with code `1` occurred, but the specific internal cause has not been confirmed. This controlled test remains additional verification work.

## 8. Recovery Procedure

The recovery procedure is:

1. Preserve the existing logs and SQLite history.
2. Inspect the supervisor log to identify the worker exit code and restart attempt.
3. Allow the supervisor to perform its configured three-second restart.
4. Confirm that a replacement worker starts with a new PID.
5. Check the application health endpoint and dashboard.
6. Confirm that new sensor readings are recorded in SQLite.
7. Check alert behavior and confirm that the system reports an appropriate health state.

The documented October 15 recovery used the supervisor's automatic restart mechanism. The existing history and logs were retained rather than deleting the database or rebuilding the project.

## 9. Verification of Recovery

The October 15 evidence confirms that the supervisor launched a replacement worker and that the dashboard and SQLite history remained usable.

On October 18, the health endpoint returned a healthy state, a latest accepted reading of 25.76°C, and `stale: false`. This supports the conclusion that the monitoring system was healthy at the time of that check, but it is not by itself proof of a new failure-recovery experiment.

The automated tests were run on October 18 and produced the following result:

`7 passed in 0.28s`

The tests include supervisor logging checks for exit codes `-9`, `1`, and `0`. These tests verify the logging behavior; they do not independently prove that a replacement worker was launched.

A new end-to-end failure experiment should additionally verify that readings resume, SQLite remains available, the dashboard responds, alert activation and clearing still work, and health returns to the expected state.
### Additional recovery verification — October 18, 2026

A new failure experiment was conducted on October 18. The sensor worker, PID 5110, was forcibly terminated. The supervisor detected exit code -9 and launched replacement worker PID 5595 approximately three seconds later.

The Flask health endpoint subsequently returned HTTP 200 with health state `HEALTHY`, latest accepted reading 23.8°C, sample number 1917, and `stale: false`. The health response timestamp was 18:37:50 UTC.

SQLite was then opened successfully without modifying the database. The database contained 1,936 rows in `readings`, 3 rows in `monitor_state`, and 0 rows in `alerts` at the time of inspection. These results support database availability and history retention after recovery. Alert activation and clearing were not re-tested as part of this failure experiment.

Evidence was saved in `evidence/recovery_test_2026-10-18.txt`, `evidence/health_after_recovery.txt`, and `evidence/database_after_recovery.txt`.
## 10. What the Logs Told Me

The supervisor log records when the supervisor starts, when a worker starts, the worker PID, the exit code, and the configured restart delay. These events make the recovery sequence visible and allow the original worker to be distinguished from its replacement.

The October 15 evidence shows that a worker termination was detected and followed by a replacement process. The later exit-code-`1` entries show why repeated restarts should be investigated rather than assumed to solve the underlying problem.

The updated logging function also includes the PID in the worker-exit warning, which makes the event more useful when correlating multiple worker processes.

## 11. What the Logs Did Not Tell Me

The supervisor log alone does not explain why a worker exited. An exit code identifies the process result but is not a complete root-cause diagnosis.

The available records do not identify the source of an external termination, explain the repeated exit-code-`1` events, or provide a complete synchronized timeline of sensor readings, dashboard requests, database operations, and alert changes.

The records also do not independently prove that all downstream functions were healthy after every restart. Additional application error logging and automated end-to-end verification would provide stronger evidence.

## 12. Improvement Made

The supervisor's worker-exit logging was improved.

The new `log_worker_exit(pid, exit_code)` function records the worker PID, exit code, and configured restart delay in a consistent warning message. This makes it easier to identify which process stopped and what recovery action was scheduled.

A new `test_supervisor_recovery.py` file adds parameterized tests for exit codes `-9`, `1`, and `0`. The test suite passes seven tests in total.

The new tests make the logging improvement repeatable and verifiable. They test the exit-message content without terminating a real worker or modifying the live SQLite database.

## 13. Remaining Limitations

The project uses replayed CSV data rather than a physical sensor. The supervisor can restart the worker while the supervisor itself remains running, but it does not independently recover if the supervisor process or the entire computer stops.

The existing October 15 evidence demonstrates worker recovery, but a fresh end-to-end failure test has not been established by the October 18 automated test run. The cause of the repeated exit-code-`1` events also remains unresolved.

Future improvements should capture worker standard error and tracebacks, record structured events with timestamps and process identifiers, and add automated integration tests for worker restart, resumed readings, database availability, dashboard health, and alert behavior.
