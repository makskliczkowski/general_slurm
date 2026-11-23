#!/usr/bin/env bash
# Submits one job per input of the chosen set; replace this line, the sets and the job script with yours.
# usage: launcher.sh small|large [--print]
# example: launcher.sh small --print
# Placement comes from the cluster settings (gs env); logs go to GS_LOG_ROOT/<date>_<set>/. Every job of one launch shares GS_SWEEP.
set -euo pipefail
source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"

# ---- arguments ----
gs_positional SET "small or large"
gs_flag --print PRINT "show the sbatch lines, submit nothing"
gs_parse "$@"

# ---- the inputs of each set ----
case "${SET}" in
    small)
        INPUTS=(a b)
        ;;
    large)
        INPUTS=(a b c d)
        ;;
    *)
        gs_die "unknown set ${SET}" 2
        ;;
esac

# ---- placement and log folder ----
gs_placement
LOGS="$(gs_logs "${SET}")"
if (( ! PRINT )); then
    mkdir -p "${LOGS}"
fi

# ---- one job per input ----
for input in "${INPUTS[@]}"; do
    gs_sbatch "${PRINT}" GS_SWEEP="${GS_SWEEP:-${SET}}" -- \
        --job-name="${SET}-${input}" --output="${LOGS}/%x_%j.log" "${GS_PLACEMENT[@]}" "$(dirname "$0")/job.slurm" "${input}"
done
