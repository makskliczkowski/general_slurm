#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --signal=B:USR1@600
#SBATCH --requeue
#SBATCH --open-mode=append
# Computes INPUT in steps; replace this line and the work section with what the job does.
# usage: job.slurm INPUT [--steps N] [--print]
# example: sbatch job.slurm in.h5 --steps 500
# Results: GS_DATA/<input name>/. The same arguments run it locally with bash and on the cluster with sbatch.
set -euo pipefail
source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"

# ---- arguments and settings ----
gs_positional INPUT "the input file"
gs_option --steps STEPS 100 "number of steps"
gs_flag --print PRINT "show the plan, compute nothing"
gs_parse "$@"
gs_path GS_DATA "the root of the result folders"
OUT="${GS_DATA}/$(basename "${INPUT%.*}")"

# ---- preview ----
if (( PRINT )); then
    echo "would compute ${INPUT} (${STEPS} steps) into ${OUT}"
    gs_print_settings
    exit 0
fi

# ---- header and data folder ----
gs_frame "$@"
gs_job
gs_data "${OUT}"

# ---- the work ----
for (( step = 0; step < STEPS; step++ )); do
    gs_progress "$(( step + 1 ))" "${STEPS}"
done
