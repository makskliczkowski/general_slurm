#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --signal=B:USR1@600
#SBATCH --requeue
#SBATCH --open-mode=append
# One array task: runs GS_COMMAND once per config of GS_CONFIGS, with its shard of each, and requeues itself while runs are left.
#
# usage: GS_CONFIGS="a.ini b.ini" GS_COMMAND="python run.py {}" sbatch jobs/shards.slurm
# example: GS_CONFIGS=a.ini GS_COMMAND="echo {}" bash jobs/shards.slurm      (one local task)
# gs submit and gs table set the variables and submit it. With GS_VENV set, the virtualenv of the repository (GS_ROOT) is built first, with the
# pip extras of GS_EXTRAS, and "{GS_PYTHON}" in GS_COMMAND is its Python. Otherwise GS_MODULES are still loaded via gs_modules. Ten minutes
# before the time limit the program gets SIGTERM and writes its checkpoint; the task requeues itself when runs are left (lib/requeue.sh).
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : shards.slurm
# -----------------------------------------------
set -euo pipefail

source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"
gs_frame "$@"
gs_need GS_CONFIGS "the config files, space separated"
gs_need GS_COMMAND "the command run per config, with {} for the config"
gs_job
gs_sweep

gs_setup_env

read -ra configs <<< "${GS_CONFIGS}"
read -ra command <<< "${GS_COMMAND}"
gs_run_each "${configs[@]}" -- "${command[@]}"
gs_finish

# -------------------------------------------
#! EOF
# -------------------------------------------
