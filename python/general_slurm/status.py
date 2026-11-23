r"""
A status file of runs: one tab-separated line per run, shared by every task of an array.

The task that creates the file writes the header. Each line is one ``write`` in append mode, so lines of concurrent tasks stay whole.

-----------------------------------------------
Author          : Maks Kliczkowski
File            : status.py
-----------------------------------------------
"""

from __future__ import annotations

import os
from datetime   import datetime
from pathlib    import Path
from typing     import Mapping, Sequence


def append_status(path: str | Path, fields: Mapping[str, object], columns: Sequence[str]) -> str:
    """
    Append one line to the status file at ``path``, with the time first and then ``fields`` in the order of ``columns``.

    Parameters
    ----------
    path : str or Path
        The status file, created with a header line when missing.
    fields : Mapping[str, object]
        Values by column; a missing column is empty. Tabs and newlines in a value become spaces.
    columns : Sequence[str]
        The columns after ``time``.

    Returns
    -------
    str
        The line written, without its newline.
    """
    path    = Path(path)
    values  = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + [str(fields.get(column, "")).replace("\t", " ").replace("\n", " ") for column in columns]
    line    = "\t".join(values)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.write(descriptor, ("\t".join(["time", *columns]) + "\n").encode())
        os.close(descriptor)
    except FileExistsError:
        pass
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
    os.write(descriptor, (line + "\n").encode())
    os.close(descriptor)
    return line

# -------------------------------------------
#! EOF
# -------------------------------------------
