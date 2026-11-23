#!/usr/bin/env bash
# The settings of the library: where each one is usually set, and where the value of a variable in this shell comes from.
#
# GS_SETTINGS lists "NAME level". The level is where a setting usually belongs: cluster (same for every project on a cluster), project
# (a path or a choice of one project that differs between clusters), repository (the same on every cluster, kept in slurm.env) or run
# (chosen per run). Any setting can also be set one level more specific; the level only says where to look first.
# A name that is not in the list is a variable of the project (project level). gs_setting_where NAME prints the command or file that sets it. gs_setting_source NAME prints which file defines the value now, in the
# order of precedence: project settings for the cluster, cluster settings, slurm.env, else the shell.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : settings.sh
# -----------------------------------------------

GS_SETTINGS=(
    "GS_PARTITION           cluster"
    "GS_GRES                cluster"
    "GS_CPU_PARTITION       cluster"
    "GS_MAX_HOURS           cluster"
    "GS_TARGET_HOURS        cluster"
    "GS_MAX_RESTARTS        cluster"
    "GS_MODULES             cluster"
    "GS_LOG_ROOT            cluster"
    "GS_TAG                 cluster"
    "SBATCH_NO_REQUEUE      cluster"
    "GS_DATA                project"
    "GS_VENV                project"
    "GS_COMMAND             repository"
    "GS_REQUIRED            repository"
    "GS_EXTRAS              repository"
    "GS_CONFIG_SUFFIX       repository"
    "GS_ROW_ARGS            repository"
    "GS_MARGIN              run"
    "GS_SWEEP               run"
)

gs_setting_where() {
    local entry
    local name
    local level
    for entry in "${GS_SETTINGS[@]}"; do
        read -r name level <<< "${entry}"
        if [[ "${name}" == "$1" ]]; then
            break
        fi
        # a name that is not in the table is a variable of the project itself
        level=project
    done
    case "${level}" in
        cluster)
            echo "gs env set ${GS_CLUSTER:-CLUSTER} $1 VALUE"
            ;;
        project)
            echo "gs env set ${GS_CLUSTER:-CLUSTER} $1 VALUE --project ${GS_PROJECT:-PROJECT}, or slurm.env when it is the same on every cluster"
            ;;
        run)
            echo "the environment of the run, $1=VALUE"
            ;;
        *)
            echo "slurm.env: $1=VALUE"
            ;;
    esac
}

# Succeeds when FILE exists and has a line matching the extended regex PATTERN.
gs_file_has() {
    [[ -f "$1" ]] && grep -qE "$2" "$1"
}

gs_setting_source() {
    local name="$1"
    local config="${GS_CONFIG_DIR:-${HOME}/.config/general_slurm}"
    if [[ -n "${GS_PROJECT:-}" && -n "${GS_CLUSTER:-}" ]] && gs_file_has "${config}/${GS_PROJECT}/${GS_CLUSTER}.sh" "^export ${name}="; then
        echo "project settings for ${GS_CLUSTER}"
    elif [[ -n "${GS_CLUSTER:-}" ]] && gs_file_has "${config}/${GS_CLUSTER}.sh" "^export ${name}="; then
        echo "cluster settings of ${GS_CLUSTER}"
    elif [[ -n "${GS_ROOT:-}" ]] && gs_file_has "${GS_ROOT}/slurm.env" "^[[:space:]]*${name}="; then
        echo "slurm.env"
    else
        echo "shell"
    fi
}

# -------------------------------------------
#! EOF
# -------------------------------------------
