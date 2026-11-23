r"""
The share of one array task and the deadline checks of the contract.

``shard`` splits the work into equal contiguous blocks, assigned before finished work is skipped, so that tasks that start at different times
still split it the same way. ``fits`` and ``fresh_allocation_fits`` decide whether a run may start, and whether a run that cannot start now
could start in a new allocation at all; when it could not, a requeue would meet the same limit, and the program exits with ``FAILED``.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : shards.py
-----------------------------------------------
"""

from __future__ import annotations

from time   import time
from typing import Sequence, TypeVar

Item = TypeVar("Item")

# The time kept free before the deadline, in seconds: the stop signal comes ten minutes before the time limit (#SBATCH --signal).
STOP_MARGIN = 600.0


def shard(items: Sequence[Item], index: int, count: int) -> list[Item]:
    """
    Block ``index`` of ``count`` equal contiguous blocks of ``items``; the blocks of all indices cover ``items`` once.

    Parameters
    ----------
    items : Sequence
        The whole work, in a fixed order.
    index, count : int
        The block and the number of blocks, ``0 <= index < count``.

    Returns
    -------
    list
        The items of the block.
    """
    return list(items[index * len(items) // count:(index + 1) * len(items) // count])


def fits(budget: float | None, deadline: float | None, now: float | None = None) -> bool:
    """
    Whether a run with ``budget`` seconds and the stop margin fits before ``deadline``; always true without a budget or a deadline.

    Parameters
    ----------
    budget : float or None
        Wall-time budget of one run in seconds.
    deadline : float or None
        End of the allocation in seconds since the epoch.
    now : float, optional
        The present time, ``time.time()`` by default.

    Returns
    -------
    bool
    """
    if budget is None or deadline is None:
        return True
    return (time() if now is None else now) + budget + STOP_MARGIN <= deadline


def fresh_allocation_fits(budget: float, deadline: float, allocation_start: float, process_start: float, now: float | None = None) -> bool:
    """
    Whether a run could start in a new allocation of the same length: the allocation less this process's start-up must hold the budget and
    the stop margin.

    Parameters
    ----------
    budget : float
        Wall-time budget of one run in seconds.
    deadline, allocation_start : float
        End and start of the allocation in seconds since the epoch.
    process_start : float
        Start of this process in seconds since the epoch; ``now - process_start`` is the start-up a new allocation would also need.
    now : float, optional
        The present time, ``time.time()`` by default.

    Returns
    -------
    bool
    """
    startup = (time() if now is None else now) - process_start
    return (deadline - allocation_start) - startup >= budget + STOP_MARGIN

# -------------------------------------------
#! EOF
# -------------------------------------------
