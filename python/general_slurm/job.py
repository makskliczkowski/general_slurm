r"""
Facts of the current job with local defaults, so a program runs the same way locally and under Slurm (as ``gs_job`` in ``lib/job.sh``).

-----------------------------------------------
Author          : Maks Kliczkowski
File            : job.py
-----------------------------------------------
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    """
    The current job: ``job_id`` (``"local"`` outside Slurm), ``task`` and ``tasks`` of an array (0 and 1 outside one), ``restarts`` (0 before
    the first requeue) and ``cpus`` (1 outside Slurm).
    """

    job_id      : str
    task        : int
    tasks       : int
    restarts    : int
    cpus        : int

    @classmethod
    def from_environment(cls) -> "Job":
        """Read the Slurm variables, with the local defaults."""
        environment = os.environ
        return cls(
            job_id      = environment.get("SLURM_JOB_ID", "local"),
            task        = int(environment.get("SLURM_ARRAY_TASK_ID", 0)),
            tasks       = int(environment.get("SLURM_ARRAY_TASK_COUNT", 1)),
            restarts    = int(environment.get("SLURM_RESTART_COUNT", 0)),
            cpus        = int(environment.get("SLURM_CPUS_PER_TASK", 1)),
        )

    @property
    def requeued(self) -> bool:
        """Whether this is a restart of a requeued job, which continues from its checkpoints."""
        return self.restarts > 0

# -------------------------------------------
#! EOF
# -------------------------------------------
