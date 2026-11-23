r"""
Example Python program that follows the sharding contract of general_slurm, with the standard library only.

usage: run.py CONFIG [--out DIR] [--shard k/n] [--deadline EPOCH] [--allocation-start EPOCH]
example: python scripts/run.py runs/a.toml --out out --shard 0/2

CONFIG has one line ``runs = N``. The program does block k of n equal blocks of the N runs and ignores the deadline, because each run here is
instant. A real program starts a run only when it fits before the deadline, and exits 130 when runs are left. The package general_slurm
provides these checks (``shard``, ``fits``, ``stop_on_signals``) for a project that installs it into its virtualenv.
With ``--out DIR`` it appends one line per run to ``DIR/<config name>.txt``. The project gets DIR from its own variable FIT_SCRATCH.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : run.py
-----------------------------------------------
"""

import argparse
import sys
from pathlib import Path


def read_runs(path: str) -> int:
    """The value of the line ``runs = N`` of the config."""
    with open(path) as handle:
        for line in handle:
            key, _, value = line.partition("=")
            if key.strip() == "runs":
                return int(value)
    raise ValueError(f"{path}: no line 'runs = N'")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example run of one config.")
    parser.add_argument("config")
    parser.add_argument("--out", help="folder of the result lines")
    parser.add_argument("--shard", default="0/1", help="k/n: block k of n equal blocks of the runs")
    parser.add_argument("--deadline", type=float)
    parser.add_argument("--allocation-start", type=float)
    args = parser.parse_args(argv)

    block, blocks = (int(part) for part in args.shard.split("/"))
    runs  = read_runs(args.config)
    first = block * runs // blocks
    last  = (block + 1) * runs // blocks
    result = None
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        result = open(Path(args.out) / f"{Path(args.config).stem}.txt", "a")
        print(f"gs: data={args.out}")
    for run in range(first, last):
        if result:
            result.write(f"run {run}\n")
        print(f"run {run} of {args.config}")
        print(f"gs: progress={run - first + 1}/{last - first}", flush=True)
    if result:
        result.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -------------------------------------------
#! EOF
# -------------------------------------------
