"""Wall-clock progress for the agent; no scientific inputs or fit decisions."""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import json
import sys
from threading import Event, RLock, Thread
from time import monotonic


_active = None


class CommandProgress:
    def __init__(self, clock=monotonic, stream=None, interval=30.0):
        self.clock = clock
        self.stream = stream if stream is not None else sys.stderr
        self.interval = interval
        self.started = clock()
        self.phase = None
        self.phase_provider = None
        self.lock = RLock()
        self.stop = Event()

    def snapshot(self):
        with self.lock:
            now = self.clock()
            elapsed = max(0.0, now - self.started)
            result = dict(elapsed_seconds=elapsed, report_total_duration=elapsed > 60.0,
                          remaining_seconds=None, estimate_status="insufficient_completed_work")
            if self.phase is not None:
                result.update(self.phase)
                result["estimate_age_seconds"] = max(0.0, now - self.phase["measured_at"])
                result.pop("measured_at")
            if self.phase_provider is not None:
                result.update(self.phase_provider(now))
            return result

    def emit(self, event="progress"):
        payload = dict(event=event, **self.snapshot())
        try:
            with self.lock:
                print("NuSrcAgent progress: " + json.dumps(payload, sort_keys=True),
                      file=self.stream, flush=True)
        except (OSError, ValueError):
            pass  # A closed progress stream must not interrupt scientific execution.

    def heartbeat(self):
        while not self.stop.wait(self.interval):
            self.emit()


@contextmanager
def command_progress(**options):
    global _active
    previous = _active
    progress = CommandProgress(**options)
    _active = progress
    progress.emit("started")
    thread = Thread(target=progress.heartbeat, daemon=True)
    thread.start()
    outcome = "finished"
    try:
        yield progress
    except BaseException:
        outcome = "interrupted_or_failed"
        raise
    finally:
        progress.stop.set()
        thread.join()
        progress.emit(outcome)
        _active = previous


def timed_command(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with command_progress():
            return function(*args, **kwargs)
    return wrapped


def print_result(result):
    """Keep stdout JSON parseable; timing is observational metadata only."""
    if _active is not None and isinstance(result, dict):
        result = dict(result, execution_timing=_active.snapshot())
    print(json.dumps(result, indent=2, sort_keys=True))


def update_work_progress(phase, completed, total, elapsed):
    """Record completed parallel work using scheduler wall time, not summed CPU time."""
    if _active is None:
        return
    remaining = None
    status = "no_known_endpoint" if total is None else "insufficient_completed_work"
    if total is not None and completed > 0:
        remaining = max(0.0, elapsed) / completed * max(0, total - completed)
        status = "estimated_from_completed_work"
    elif total == 0:
        remaining, status = 0.0, "no_remaining_units"
    with _active.lock:
        _active.phase = dict(phase=phase, completed_units=completed, total_units=total,
            phase_elapsed_seconds=max(0.0, elapsed), remaining_seconds=remaining,
            estimate_status=status, estimate_scope="current_phase_only",
            measured_at=_active.clock())
    _active.emit()


def track_progress(items, phase, total=None, skip=None):
    """Estimate this phase from completed units in this invocation only.

    Exclude restored checkpoints before calling. Do not mix rates from different
    fit procedures, phases or worker configurations. Unknown totals stay unknown.
    """
    progress = _active
    if progress is None:
        yield from items
        return
    if total is None:
        try:
            total = len(items)
        except TypeError:
            pass
    if skip is not None:
        items = list(items)
        total = sum(not skip(item) for item in items)
    started = progress.clock()
    completed = 0
    with progress.lock:
        previous = progress.phase

    def update():
        now = progress.clock()
        elapsed = max(0.0, now - started)
        update_work_progress(phase, completed, total, elapsed)

    update()
    try:
        for item in items:
            already_completed = skip is not None and skip(item)
            yield item
            if not already_completed:
                completed += 1
                update()
    finally:
        with progress.lock:
            progress.phase = previous
