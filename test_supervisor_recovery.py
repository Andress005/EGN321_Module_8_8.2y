
import logging

import pytest

from supervisor import log_worker_exit, RESTART_DELAY_SECONDS


@pytest.mark.parametrize(
    ("pid", "exit_code"),
    [
        (12345, -9),
        (23456, 1),
        (34567, 0),
    ],
)
def test_worker_exit_is_logged_with_pid_and_exit_code(
    caplog, pid, exit_code
):
    with caplog.at_level(logging.WARNING, logger="sensor_supervisor"):
        log_worker_exit(pid, exit_code)

    message = caplog.text

    assert str(pid) in message
    assert str(exit_code) in message
    assert str(RESTART_DELAY_SECONDS) in message
    assert "restarting" in message.lower()
