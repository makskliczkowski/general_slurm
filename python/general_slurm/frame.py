r"""
The log lines of the bash library, from Python: header, tagged facts, data folder, progress, checkpoint and metric.

Tagged lines start with the environment variable ``GS_TAG`` (default ``gs:``), as in ``lib/frame.sh``, so one log reader parses the logs of
bash and Python jobs alike.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : frame.py
-----------------------------------------------
"""

from __future__ import annotations

import os
import socket
import sys
from datetime   import datetime
from pathlib    import Path


def _tag() -> str:
    return os.environ.get("GS_TAG", "gs:")


def _say(line: str) -> None:
    print(line, flush=True)


def info(key: str, text: object) -> None:
    """One fact of the run, ``<tag> info KEY=TEXT``."""
    _say(f"{_tag()} info {key}={text}")


def progress(done: int, total: int) -> None:
    """``<tag> progress=DONE/TOTAL``."""
    _say(f"{_tag()} progress={done}/{total}")


def checkpoint(path: str | Path) -> None:
    """``<tag> checkpoint=/abs/path`` after a save."""
    _say(f"{_tag()} checkpoint={Path(path).resolve()}")


def metric(name: str, value: object) -> None:
    """``<tag> metric NAME=VALUE``."""
    _say(f"{_tag()} metric {name}={value}")


def data(folder: str | Path) -> Path:
    """
    Create the data folder, print ``<tag> data=/abs/path`` and append the job, script and date to its ``job.txt``.

    Returns
    -------
    Path
        The absolute folder.
    """
    folder  = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    _say(f"{_tag()} data={folder}")
    job     = os.environ.get("SLURM_JOB_ID", "local") + (f" task {os.environ['SLURM_ARRAY_TASK_ID']}" if "SLURM_ARRAY_TASK_ID" in os.environ else "")
    with open(folder / "job.txt", "a") as stream:
        stream.write(f"job      {job}\nscript   {Path(sys.argv[0]).resolve()}\ndate     {datetime.now().isoformat(timespec='seconds')}\n")
    return folder


def frame() -> None:
    """The header, ``== NAME job ID task T on NODE at DATE`` and ``== in DIR: ARGS``."""
    name    = os.environ.get("SLURM_JOB_NAME", Path(sys.argv[0]).name)
    job     = f" job {os.environ['SLURM_JOB_ID']}" if "SLURM_JOB_ID" in os.environ else ""
    task    = f" task {os.environ['SLURM_ARRAY_TASK_ID']}" if "SLURM_ARRAY_TASK_ID" in os.environ else ""
    _say(f"== {name}{job}{task} on {socket.gethostname()} at {datetime.now().astimezone().isoformat(timespec='seconds')}")
    _say(f"== in {os.getcwd()}: {' '.join(sys.argv[1:])}")

# -------------------------------------------
#! EOF
# -------------------------------------------
