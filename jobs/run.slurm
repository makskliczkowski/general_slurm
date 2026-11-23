#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --open-mode=append
# One single Slurm job: loads modules or virtualenv, prints the log frame, expands environment placeholders, and runs the given command.
#
# usage: sbatch jobs/run.slurm COMMAND [ARGUMENT...]
# example: GS_MODULES="gcc/13" bash jobs/run.slurm ./build/sim inputs/a.cfg
# gs run submits this script when given a command instead of a .slurm file. With GS_VENV set, the repository virtualenv is built first and
# "{GS_PYTHON}" expands to its Python; otherwise GS_MODULES are loaded via gs_modules. Every "{NAME}" placeholder in the arguments expands to
# the environment variable NAME.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : run.slurm
# -----------------------------------------------
set -euo pipefail

source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"
if (( $# == 0 )); then
    gs_die "give a command to run" 2
fi

gs_frame "$@"
gs_job
gs_sweep

gs_setup_env

command=()
for word in "$@"; do
    command+=("$(gs_expand_names "${word}")")
done

"${command[@]}"

# -------------------------------------------
#! EOF
# -------------------------------------------