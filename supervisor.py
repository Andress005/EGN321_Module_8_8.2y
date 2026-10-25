
import logging
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "supervisor.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sensor_supervisor")

RESTART_DELAY_SECONDS = 3


def log_worker_exit(pid, exit_code):
    """Log worker failure details before attempting recovery."""
    logger.warning(
        "Worker PID %s stopped with exit code %s; "
        "restarting in %s seconds",
        pid,
        exit_code,
        RESTART_DELAY_SECONDS,
    )


def main():
    logger.info("Supervisor started")
    process = None

    try:
        while True:
            logger.info("Starting virtual sensor worker")

            process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    str(BASE_DIR / "run_monitor.py"),
                ],
                cwd=BASE_DIR,
            )

            logger.info("Worker started with PID %s", process.pid)

            while process.poll() is None:
                time.sleep(1)

            exit_code = process.returncode
            log_worker_exit(process.pid, exit_code)

            time.sleep(RESTART_DELAY_SECONDS)

    except KeyboardInterrupt:
        logger.info("Supervisor shutdown requested")

    finally:
        if process is not None and process.poll() is None:
            logger.info(
                "Stopping worker PID %s during supervisor shutdown",
                process.pid,
            )
            process.terminate()

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Worker PID %s did not stop; forcing termination",
                    process.pid,
                )
                process.kill()
                process.wait()

        logger.info("Supervisor stopped")


if __name__ == "__main__":
    main()
