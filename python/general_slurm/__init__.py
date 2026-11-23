r"""
Python side of general_slurm: what a program run by ``jobs/shards.slurm`` needs to follow the contract.

The contract: the program accepts ``--shard k/n``, ``--deadline EPOCH`` and ``--allocation-start EPOCH`` (``cli.add_arguments``), runs only
its shard of the work (``shards.shard``), starts a run only when its budget fits before the deadline (``shards.fits``), checkpoints when it
gets SIGTERM (``signals.stop_on_signals``, ``signals.held_signals``), and exits with ``DONE`` when its runs are done, ``LEFT`` when runs are
left and ``FAILED`` after a failure. The log lines (``frame``) are those of the bash library.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : __init__.py
-----------------------------------------------
"""

from .cli       import add_arguments, parse_shard
from .frame     import checkpoint, data, frame, info, metric, progress
from .job       import Job
from .shards    import fits, fresh_allocation_fits, shard
from .signals   import budget_alarm, held_signals, stop_on_signals
from .status    import append_status
from .table     import pack, read_table, row

# Exit statuses of the contract: the job script requeues on LEFT and reports FAILED.
DONE    = 0
FAILED  = 1
LEFT    = 130

__version__ = "0.1.0"

__all__ = [
    "DONE",
    "FAILED",
    "LEFT",
    "Job",
    "add_arguments",
    "append_status",
    "budget_alarm",
    "checkpoint",
    "data",
    "fits",
    "frame",
    "fresh_allocation_fits",
    "held_signals",
    "info",
    "metric",
    "pack",
    "parse_shard",
    "progress",
    "read_table",
    "row",
    "shard",
    "stop_on_signals",
]

# -------------------------------------------
#! EOF
# -------------------------------------------
