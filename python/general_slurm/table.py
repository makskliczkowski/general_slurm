r"""
Tables of runs from Python: reading a table, the row of an array task, and packing, with the algorithm of ``gs_pack`` in ``lib/table.sh``.

A table line is ``CONFIG LABEL... RUNS HOURS [KEY=VALUE...] [request]``; ``#`` starts a comment. A run takes ``margin x HOURS``. Runs share a
task up to ``target`` hours; a longer run gets a task of its own. The time limit is the task's hours rounded up plus two, at most
``max_hours``. The tests check that ``pack`` and ``gs_pack`` give the same lines.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : table.py
-----------------------------------------------
"""

from __future__ import annotations

import math
from dataclasses    import dataclass
from pathlib        import Path
from typing         import Sequence


def read_table(path: str | Path) -> list[list[str]]:
    """The fields of every line of a table, without comments and blank lines."""
    rows = []
    for line in Path(path).read_text().splitlines():
        fields = line.split("#", 1)[0].split()
        if fields:
            rows.append(fields)
    return rows


def row(path: str | Path, task: int) -> list[str]:
    """The fields of row ``task`` (from 0) of a table: the row an array task runs."""
    return read_table(path)[task]


@dataclass(frozen=True)
class Array:
    """One packed table line: its config and labels, the runs, runs per task, tasks, time limit in hours and KEY=VALUE job options."""

    config      : str
    labels      : tuple[str, ...]
    runs        : int
    per_task    : int
    tasks       : int
    limit       : int
    options     : dict[str, str]


def pack(path: str | Path, max_hours: float, target: float, words: Sequence[str] = (), margin: float = 1.3) -> list[Array]:
    """
    Pack the selected lines of a table into array tasks.

    Parameters
    ----------
    path : str or Path
        The table.
    max_hours, target : float
        The job time limit of the partition and the packing target, in hours.
    words : Sequence[str]
        Every word must equal a field before RUNS; a ``request`` line is selected only when its CONFIG is a word.
    margin : float
        A run takes ``margin`` times its HOURS.

    Returns
    -------
    list[Array]
        One entry per selected line, in table order.
    """
    arrays  = []
    known   = set()
    for fields in read_table(path):
        request = fields[-1] == "request"
        fields  = fields[:-1] if request else fields
        options = {}
        while "=" in fields[-1]:
            key, value      = fields.pop().split("=", 1)
            options[key]    = value
        heads       = fields[:-2]
        runs        = int(fields[-2])
        run_hours   = margin * float(fields[-1])

        hits        = [word for word in words if word in heads]
        known.update(hits)
        if len(hits) < len(words):
            continue
        if request and fields[0] not in words:
            continue

        per_task    = min(int(target / run_hours), runs) if run_hours <= target else 1
        tasks       = math.ceil(runs / per_task)
        limit       = min(int(per_task * run_hours + 2.999), int(max_hours))
        arrays.append(Array(fields[0], tuple(heads[1:]), runs, per_task, tasks, limit, dict(reversed(list(options.items())))))
    unknown = [word for word in words if word not in known]
    if unknown:
        raise ValueError(f"unknown selection: {' '.join(unknown)}")
    return arrays

# -------------------------------------------
#! EOF
# -------------------------------------------
