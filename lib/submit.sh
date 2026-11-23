#!/usr/bin/env bash
# Submission of jobs: the placement from the cluster settings, one log folder per launch, and one call that previews or submits.
#
# gs_placement [--cpu] sets the array GS_PLACEMENT: --partition=GS_PARTITION --gres=GS_GRES, or --partition=GS_CPU_PARTITION --gres=none.
# Placement never goes into #SBATCH lines, because sbatch does not expand variables there; a new cluster is configured in its settings file alone (gs env).
# gs_logs TAG prints the log folder of one launch, GS_LOG_ROOT/<date>_<TAG> (GS_LOG_ROOT defaults to logs).
# gs_sbatch PRINT [NAME=VALUE...] -- SBATCH_ARGUMENTS... prints the line when PRINT is 1, else submits it with those variables in its
# environment and prints "submitted JOBID". Each submission appends "JOBID<tab>DATE<tab>LINE" to GS_LOG_ROOT/submissions.tsv, so that
# gs rerun can submit the same line again; gs rerun therefore runs from the folder the job was submitted from.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : submit.sh
# -----------------------------------------------

gs_placement() {
    if [[ "${1:-}" == --cpu ]]; then
        gs_need GS_CPU_PARTITION "the CPU partition"
        GS_PLACEMENT=(--partition="${GS_CPU_PARTITION}" --gres=none)
    else
        gs_need GS_PARTITION "the GPU partition"
        gs_need GS_GRES "the GPU request, fully qualified where the cluster asks for it (gpu:a100:1)"
        GS_PLACEMENT=(--partition="${GS_PARTITION}" --gres="${GS_GRES}")
    fi
}

gs_logs() {
    echo "${GS_LOG_ROOT:-logs}/$(date +%F)_$1"
}

gs_sbatch() {
    local print="$1"
    local -a variables=()
    local line
    local job
    shift
    while (( $# )) && [[ "$1" != -- ]]; do
        variables+=("$1")
        shift
    done
    shift
    # the line is quoted, so that it can be pasted into a terminal and read back by gs rerun
    printf -v line '%q ' ${variables[@]+"${variables[@]}"} sbatch "$@"
    line="${line% }"
    if (( print )); then
        echo "${line}"
        return
    fi
    # --parsable prints JOBID or JOBID;CLUSTER
    job="$(env ${variables[@]+"${variables[@]}"} sbatch --parsable "$@")"
    job="${job%%;*}"
    mkdir -p "${GS_LOG_ROOT:-logs}"
    printf '%s\t%s\t%s\n' "${job}" "$(date '+%F %T')" "${line}" >> "${GS_LOG_ROOT:-logs}/submissions.tsv"
    echo "submitted ${job}"
}

# -------------------------------------------
#! EOF
# -------------------------------------------
