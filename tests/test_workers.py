"""JobRunner tests with a fake tkinter app (no display needed)."""

from __future__ import annotations

import time

from trade_dashboard_desktop.ui.workers import Job, JobRunner


class FakeApp:
    """Stands in for tk.Tk: records after() callbacks instead of running a loop."""

    def __init__(self):
        self.scheduled = []

    def after(self, ms, callback):
        self.scheduled.append((ms, callback))

    def pump(self):
        """Run one scheduled callback, like the tkinter main loop would."""
        _, callback = self.scheduled.pop(0)
        callback()


def _wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_job_success_delivers_value():
    app = FakeApp()
    runner = JobRunner(app)
    received = []
    runner.submit(Job("t", lambda: 42, on_done=received.append))
    assert _wait_for(lambda: not runner._results.empty())
    app.pump()  # like the main loop firing the poll callback
    assert received == [42]


def test_job_error_delivers_message():
    app = FakeApp()
    runner = JobRunner(app)

    def boom():
        raise RuntimeError("kaput")

    errors = []
    runner.submit(Job("t", boom, on_error=errors.append))
    assert _wait_for(lambda: not runner._results.empty())
    app.pump()
    assert len(errors) == 1 and errors[0].startswith("RuntimeError: kaput")


def test_submit_schedules_polling():
    app = FakeApp()
    runner = JobRunner(app)
    runner.submit(Job("t", lambda: None))
    assert runner.running >= 1
    assert app.scheduled, "expected app.after to be scheduled"
    assert app.scheduled[0][0] == JobRunner.POLL_MS


def test_poll_stops_when_idle():
    app = FakeApp()
    runner = JobRunner(app)
    runner.submit(Job("t", lambda: 1, on_done=lambda v: None))
    assert _wait_for(lambda: not runner._results.empty())
    app.pump()
    assert runner.running == 0
    assert runner._polling is False
    assert not app.scheduled, "no further polls should be scheduled when idle"
