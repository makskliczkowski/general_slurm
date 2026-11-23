#!/usr/bin/env bash
# Runs that survive the time limit: run a command once per config file, forward the stop signals, and requeue the job while runs are left.
#
# gs_run_each CONFIG... -- COMMAND... runs COMMAND once per CONFIG, one after another. In COMMAND, "{}" is the config and "{NAME}" the value of
# the environment variable NAME. Each run gets "--shard k/n" (this array task of n) and, when the job has an end time, "--deadline EPOCH
# --allocation-start EPOCH". The program follows the contract: exit 0 when its runs are done, 130 when runs are left, any other status on
# failure, and a checkpoint on SIGTERM. Slurm sends USR1 before the time limit (#SBATCH --signal=B:USR1@600); scancel sends TERM. Both are
# forwarded to the running program as TERM. gs_finish then requeues the job (scontrol requeue, #SBATCH --requeue) when runs are left after
# USR1 or after a stop by the program's own budget, never after a scancel, at most GS_MAX_RESTARTS times (default 10). A job that cannot
# requeue exits nonzero, so that Slurm does not show it as completed.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : requeue.sh
# -----------------------------------------------

# The end of this job's allocation in seconds since the epoch, or nothing when the job has no end time.
gs_deadline() {
    local end
    end="$(squeue -h -j "${SLURM_JOB_ID:-0}" -o %e 2>/dev/null || true)"
    if [[ -n "${end}" && "${end}" != N/A ]]; then
        date -d "${end}" +%s 2>/dev/null || true
    fi
}

# The newest file in a checkpoint folder, or nothing.
gs_latest() {
    if [[ -d "$1" ]]; then
        ls -t "$1" 2>/dev/null | head -n 1 | sed "s|^|$1/|"
    fi
}

# The signal handlers: TERM (scancel) stops without a requeue, USR1 (the time limit) stops with one. No program may be running when a signal
# comes, so the kill may fail, and "|| true" keeps set -e from ending the script inside the handler.
gs_on_term() {
    GS_STOP=1
    kill -TERM "${GS_PID}" 2>/dev/null || true
}

gs_on_usr1() {
    GS_STOP=1
    GS_REQUEUE=1
    kill -TERM "${GS_PID}" 2>/dev/null || true
}

# One word with "{NAME}" replaced by the value of NAME.
gs_expand_names() {
    local word="$1"
    local name
    while [[ "${word}" =~ \{([A-Za-z_][A-Za-z0-9_]*)\} ]]; do
        name="${BASH_REMATCH[1]}"
        word="${word//\{${name}\}/${!name:-}}"
    done
    echo "${word}"
}

# One word of a command with "{}" replaced by the config and "{NAME}" by the value of NAME.
gs_expand() {
    gs_expand_names "${1//\{\}/$2}"
}

gs_run_each() {
    local -a configs=()
    local -a template=()
    local -a command=()
    local config
    local word
    local status
    while (( $# )) && [[ "$1" != -- ]]; do
        configs+=("$1")
        shift
    done
    shift
    template=("$@")
    gs_job

    GS_PART_START="$(date +%s)"
    GS_DEADLINE="$(gs_deadline)"
    GS_STOP=0
    GS_REQUEUE=0
    GS_LEFT=0
    GS_EXIT=0
    GS_PID=""
    trap gs_on_term TERM
    trap gs_on_usr1 USR1

    for config in ${configs[@]+"${configs[@]}"}; do
        # a signal before this config leaves it and the later ones to the next part
        if (( GS_STOP )); then
            GS_LEFT=1
            break
        fi
        command=()
        for word in "${template[@]}"; do
            command+=("$(gs_expand "${word}" "${config}")")
        done
        command+=(--shard "${GS_TASK}/${GS_TASKS}")
        if [[ -n "${GS_DEADLINE}" ]]; then
            command+=(--deadline "${GS_DEADLINE}" --allocation-start "${GS_PART_START}")
        fi

        # in the background, so that the shell runs a trap at once instead of after the program
        "${command[@]}" &
        GS_PID=$!
        status=0
        wait "${GS_PID}" || status=$?
        # a trap interrupted the first wait: wait again for the program to finish its checkpoint
        if (( GS_STOP && status > 128 )); then
            status=0
            wait "${GS_PID}" || status=$?
        fi
        # 143 after a stop: TERM ended the program before it installed its handler, so before any run, and its runs are left
        if (( GS_STOP && status == 143 )); then
            status=130
        fi
        if (( status == 130 )); then
            GS_LEFT=1
        elif (( status != 0 )); then
            GS_EXIT=${status}
        fi
    done
}

gs_finish() {
    local max="${GS_MAX_RESTARTS:-10}"
    if (( GS_LEFT )); then
        if [[ -n "${SLURM_JOB_ID:-}" ]] && (( (GS_REQUEUE || !GS_STOP) && GS_RESTARTS < max )); then
            if scontrol requeue "${SLURM_JOB_ID}"; then
                echo "task ${GS_TASK}/${GS_TASKS} requeued with runs left: restart $(( GS_RESTARTS + 1 ))/${max}"
                exit 0
            fi
            echo "task ${GS_TASK}/${GS_TASKS}: the cluster refused the requeue. Resubmit to continue the runs left."
        else
            echo "task ${GS_TASK}/${GS_TASKS} stopped with runs left after ${GS_RESTARTS} restarts. Resubmit to continue them."
        fi
        if (( GS_EXIT != 0 )); then
            exit "${GS_EXIT}"
        fi
        exit 1
    fi
    if (( GS_EXIT != 0 )); then
        echo "task ${GS_TASK}/${GS_TASKS} failed (exit ${GS_EXIT})"
        exit "${GS_EXIT}"
    fi
    echo "task ${GS_TASK}/${GS_TASKS} finished"
}

# -------------------------------------------
#! EOF
# -------------------------------------------
