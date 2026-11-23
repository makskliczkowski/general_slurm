#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
# One task of an array: runs the row of TABLE with this task's index; replace this line and the work section with what a row does.
# usage: array.slurm TABLE [--print]
# example: sbatch --array=0-9 array.slurm runs.txt
# Results: GS_DATA/<first field of the row>/. An array of n tasks runs a table of n rows; "#" starts a comment in the table.
set -euo pipefail
source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"

# ---- arguments and settings ----
gs_positional TABLE "the table of runs, one row per task"
gs_flag --print PRINT "show the row, compute nothing"
gs_parse "$@"
gs_job
read -ra ROW <<< "$(gs_row "${TABLE}")"
if (( ${#ROW[@]} == 0 )); then
    gs_die "no row ${GS_TASK} in ${TABLE}"
fi

# ---- preview ----
if (( PRINT )); then
    echo "task ${GS_TASK} would run: ${ROW[*]}"
    exit 0
fi

# ---- header and data folder ----
gs_path GS_DATA "the root of the result folders"
gs_frame "$@"
gs_data "${GS_DATA}/${ROW[0]}"

# ---- the work: the fields of the row are ${ROW[0]}, ${ROW[1]}, ... ----
echo "running ${ROW[*]}"
