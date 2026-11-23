#!/usr/bin/env bash
# Log frame of a job script: a header, tagged lines, the data folder and the exit status, in a fixed form that a log reader can parse.
#
# gs_frame "$@" prints the header "== NAME job ID task T on NODE at DATE" and "== in DIR: ARGS" and makes the last line "== exit N at DATE".
# Tagged lines start with GS_TAG (default "gs:"): "<tag> info KEY=TEXT", "<tag> data=/abs/path", "<tag> progress=DONE/TOTAL",
# "<tag> checkpoint=/abs/path", "<tag> metric NAME=VALUE". gs_data also writes job.txt into the data folder, so data lead back to the log.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : frame.sh
# -----------------------------------------------

GS_TAG="${GS_TAG:-gs:}"

# One fact of the run: code, modules, script, git, log, sweep, resume, ...
gs_info() {
    echo "${GS_TAG} info $1=$2"
}

gs_progress() {
    echo "${GS_TAG} progress=$1/$2"
}

gs_checkpoint() {
    echo "${GS_TAG} checkpoint=$(realpath -- "$1")"
}

gs_metric() {
    echo "${GS_TAG} metric $1=$2"
}

# The data folder: created, printed early (a log reader scans the beginning of a log), and given a job.txt that names job, script and log.
gs_data() {
    local folder
    mkdir -p "$1"
    folder="$(cd "$1" && pwd -P)"
    echo "${GS_TAG} data=${folder}"
    {
        echo "job      ${SLURM_JOB_ID:-local}${SLURM_ARRAY_TASK_ID:+ task ${SLURM_ARRAY_TASK_ID}}"
        echo "script   ${GS_SCRIPT:-$0}"
        echo "log      ${GS_LOG:--}"
        echo "git      ${GS_GIT:--}"
        echo "date     $(date -Is)"
    } >> "${folder}/job.txt"
}

# The original script and log of a Slurm job ($0 is a spooled copy); empty outside Slurm.
gs_slurm_record() {
    local job
    if ! job=$(scontrol show job "${SLURM_JOB_ID:-}" -o 2>/dev/null); then
        return
    fi
    # an array query returns one record per task and one per range of pending tasks: keep the record of this task
    if [[ -n "${SLURM_ARRAY_TASK_ID:-}" ]]; then
        job=$(grep " ArrayTaskId=${SLURM_ARRAY_TASK_ID} " <<< "${job}" || true)
    fi
    if [[ $(grep -c . <<< "${job}") -eq 1 ]]; then
        echo "${job}"
    fi
}

gs_frame() {
    local record
    local folder
    record="$(gs_slurm_record)"
    GS_SCRIPT="$0"
    GS_LOG=""
    if [[ -n "${record}" ]]; then
        GS_SCRIPT="$(grep -o 'Command=[^ ]*' <<< "${record}" | cut -d= -f2)"
        GS_LOG="$(grep -o 'StdOut=[^ ]*' <<< "${record}" | cut -d= -f2)"
        gs_info log "${GS_LOG}"
    fi
    GS_SCRIPT="$(realpath -- "${GS_SCRIPT}")"
    gs_info script "${GS_SCRIPT}"
    if [[ -n "${LOADEDMODULES:-}" ]]; then
        gs_info modules "${LOADEDMODULES//:/ }"
    fi

    # branch@commit, with " +dirty" when tracked files changed; nothing outside git or before the first commit
    folder="$(dirname "${GS_SCRIPT}")"
    GS_GIT=""
    if git -C "${folder}" rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
        GS_GIT="$(git -C "${folder}" rev-parse --abbrev-ref HEAD)@$(git -C "${folder}" rev-parse --short HEAD)"
        if ! git -C "${folder}" diff --quiet HEAD --; then
            GS_GIT+=" +dirty"
        fi
        gs_info git "${GS_GIT}"
    fi
    export GS_SCRIPT GS_LOG GS_GIT

    echo "== ${SLURM_JOB_NAME:-$(basename "$0")}${SLURM_JOB_ID:+ job ${SLURM_JOB_ID}}${SLURM_ARRAY_TASK_ID:+ task ${SLURM_ARRAY_TASK_ID}} on $(hostname) at $(date -Is)"
    echo "== in ${PWD}: $*"
    trap 'echo "== exit $? at $(date -Is)"' EXIT
}

# -------------------------------------------
#! EOF
# -------------------------------------------
