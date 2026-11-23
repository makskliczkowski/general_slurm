"""Runs the configs of its shard under the general_slurm contract; replace this line and the run function with what one config does.

usage: job.py CONFIG... [--shard k/n] [--deadline EPOCH] [--allocation-start EPOCH] [--run-hours H]
example: python job.py runs/a.toml runs/b.toml --shard 0/2
Exit status: 0 when every run of the shard is done, 130 when runs are left (checkpointed or not started), 1 after a failure.
"""

import argparse
import sys
from time import time

import general_slurm as gs

PROCESS_START = time()


def run(config: str) -> None:
    """One config: replace with the work, and write a checkpoint when KeyboardInterrupt arrives."""
    gs.info("config", config)


def main(argv=None) -> int:
    parser  = gs.add_arguments(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    parser.add_argument("configs", nargs="+")
    args    = parser.parse_args(argv)
    gs.frame()
    gs.stop_on_signals()

    budget  = None if args.run_hours is None else 3600.0 * args.run_hours
    mine    = gs.shard(args.configs, *args.shard)
    failed  = 0
    for position, config in enumerate(mine):
        if not gs.fits(budget, args.deadline):
            # a run that cannot fit even into a fresh allocation would never start
            if position == 0 and args.allocation_start is not None and not gs.fresh_allocation_fits(budget, args.deadline, args.allocation_start, PROCESS_START):
                return gs.FAILED
            return gs.LEFT
        try:
            run(config)
        except KeyboardInterrupt:
            return gs.LEFT
        except Exception as error:
            print(f"{config}: {type(error).__name__}: {error}", file=sys.stderr)
            failed += 1
        gs.progress(position + 1, len(mine))
    return gs.FAILED if failed else gs.DONE


if __name__ == "__main__":
    sys.exit(main())
