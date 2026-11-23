r"""
The arguments of the contract for an ``argparse`` parser: ``--shard k/n``, ``--deadline``, ``--allocation-start`` and ``--run-hours``.

``jobs/shards.slurm`` passes the first three; ``--run-hours`` is the program's own budget per run.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : cli.py
-----------------------------------------------
"""

from __future__ import annotations

import argparse


def parse_shard(text: str) -> tuple[int, int]:
    """
    Read a shard ``k/n``: block ``k`` (from 0) of ``n`` equal blocks.

    Parameters
    ----------
    text : str
        ``"k/n"`` with ``0 <= k < n``.

    Returns
    -------
    tuple[int, int]
        ``(k, n)``.
    """
    index, count = (int(part) for part in text.split("/"))
    if not 0 <= index < count:
        raise argparse.ArgumentTypeError(f"shard {text}: need 0 <= k < n")
    return index, count


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add the arguments of the contract to ``parser`` and return it.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The program's parser.

    Returns
    -------
    argparse.ArgumentParser
        The same parser, with ``shard`` (``(k, n)``, default ``(0, 1)``), ``deadline`` and ``allocation_start`` (seconds since the epoch, or
        ``None``) and ``run_hours`` (``None`` for no budget).
    """
    parser.add_argument("--shard", type=parse_shard, default=(0, 1), help="k/n: block k (from 0) of n equal blocks of the work")
    parser.add_argument("--deadline", type=float, help="end of the allocation, seconds since the epoch: no run starts that would not fit")
    parser.add_argument("--allocation-start", type=float, help="start of the allocation, seconds since the epoch, with --deadline")
    parser.add_argument("--run-hours", type=float, help="wall-time budget of one run; a stopped run is checkpointed")
    return parser

# -------------------------------------------
#! EOF
# -------------------------------------------
