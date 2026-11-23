#!/usr/bin/env bash
# Facts of the current job with local defaults, so a script runs the same way with bash and with sbatch, and the check of a sweep name.
#
# gs_job sets GS_JOB_ID (local outside Slurm), GS_TASK and GS_TASKS (0 and 1 outside an array), GS_RESTARTS (0 before the first requeue) and
# GS_CPUS (1 outside Slurm). gs_sweep checks GS_SWEEP, the name shared by every job of one prepared sweep, and prints it as an info line.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : job.sh
# -----------------------------------------------

gs_job() {
    export GS_JOB_ID="${SLURM_JOB_ID:-local}"
    export GS_TASK="${SLURM_ARRAY_TASK_ID:-0}"
    export GS_TASKS="${SLURM_ARRAY_TASK_COUNT:-1}"
    export GS_RESTARTS="${SLURM_RESTART_COUNT:-0}"
    export GS_CPUS="${SLURM_CPUS_PER_TASK:-1}"
}

# An unset GS_SWEEP prints nothing; a set one must be 1 to 60 letters, digits or _.+- so that tools can group jobs by it.
gs_sweep() {
    if [[ -z "${GS_SWEEP:-}" ]]; then
        return
    fi
    if [[ ! "${GS_SWEEP}" =~ ^[A-Za-z0-9_.+-]{1,60}$ ]]; then
        gs_die "GS_SWEEP must be 1 to 60 letters, digits or _.+-, not: ${GS_SWEEP}" 2
    fi
    gs_info sweep "${GS_SWEEP}"
}

# -------------------------------------------
#! EOF
# -------------------------------------------
