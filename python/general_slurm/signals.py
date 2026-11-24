r"""
Stop signals of a program under the contract: a stop becomes ``KeyboardInterrupt``, a save completes before a stop takes effect, and a run
budget fires as a stop.

SIGNAL STOPPING:

``stop_on_signals`` makes SIGINT and SIGTERM raise ``KeyboardInterrupt``, which the program catches to write its checkpoint. ``held_signals``
holds those signals while a result is saved and reports afterwards whether one came, so the program saves completely and then stops.

BUDGET ALARM:

``budget_alarm`` raises ``KeyboardInterrupt`` after a number of seconds (SIGALRM), records that the budget, not a stop, ended the run, and
cancels the alarm when its block ends.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : signals.py
-----------------------------------------------
"""

from __future__ import annotations

import signal
from contextlib     import contextmanager
from dataclasses    import dataclass, field
from typing         import Iterator

STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


def _stop(signum, frame):
    raise KeyboardInterrupt


def stop_on_signals() -> None:
    """Make SIGINT and SIGTERM raise ``KeyboardInterrupt``."""
    for stop in STOP_SIGNALS:
        signal.signal(stop, _stop)


@dataclass
class Held:
    """The signals that arrived inside ``held_signals``; ``stop`` is true when SIGINT or SIGTERM came."""

    signals : list[int] = field(default_factory=list)

    @property
    def stop(self) -> bool:
        return any(signum in STOP_SIGNALS for signum in self.signals)


@contextmanager
def held_signals() -> Iterator[Held]:
    """
    Hold SIGINT, SIGTERM and SIGALRM inside the block, cancel a pending budget alarm, and restore the handlers afterwards.

    Returns
    -------
    Held
        After the block, ``held.stop`` tells whether a stop signal came; the caller then ends its work after the save.
    """
    held        = Held()
    signal.setitimer(signal.ITIMER_REAL, 0.0)
    previous    = {signum: signal.signal(signum, lambda signum, frame: held.signals.append(signum)) for signum in (*STOP_SIGNALS, signal.SIGALRM)}
    try:
        yield held
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


@dataclass
class Budget:
    """Set by ``budget_alarm``: ``expired`` is true once the budget raised ``KeyboardInterrupt``."""

    expired : bool = False


@contextmanager
def budget_alarm(seconds: float | None) -> Iterator[Budget]:
    """
    Raise ``KeyboardInterrupt`` after ``seconds`` of wall time; ``None`` sets no alarm. The block cancels the alarm and restores the
    previous SIGALRM handler when it ends, so no alarm is left for the next run.

    Parameters
    ----------
    seconds : float or None
        The run budget.

    Yields
    ------
    Budget
        ``budget.expired`` tells afterwards whether the budget, not a stop signal, interrupted the run.
    """
    budget = Budget()

    def expire(signum, frame):
        budget.expired = True
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGALRM, expire)
    if seconds:
        signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield budget
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous)

# -------------------------------------------
#! EOF
# -------------------------------------------
