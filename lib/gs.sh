#!/usr/bin/env bash
# Loader of the general_slurm bash library: a script sources this one file and gets every gs_ helper.
#
# usage: source "${GS_HOME}/lib/gs.sh"
# Cluster settings come from the environment: the ~/.bashrc loader of lib/cluster.sh exports them on a login node, and a job inherits them.
# This file loads the repository settings (the first slurm.env upwards from the working directory, KEY=VALUE lines that are read, never run;
# a variable already set wins), names the project (GS_PROJECT, default the folder of slurm.env) and sources the settings of that project on
# the cluster, which override the cluster settings and slurm.env; then the modules.
# Works with bash 3.2 and later; gs_venv needs bash 4.1 and flock (Linux).
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : gs.sh
# -----------------------------------------------

GS_VERSION="0.1.0"
GS_HOME="${GS_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export GS_HOME GS_VERSION

# Read the KEY=VALUE lines of a settings file into the environment. A key that is already set stays.
gs_load_settings() {
    local key
    local value
    while IFS='=' read -r key value || [[ -n "${key}" ]]; do
        # trim the key, skip comments and blank lines
        key="${key#"${key%%[![:space:]]*}"}"
        if [[ ! "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            continue
        fi
        # drop a trailing comment, trailing blanks and surrounding quotes
        value="${value%%#*}"
        value="${value%"${value##*[![:space:]]}"}"
        value="${value#[\"\']}"
        value="${value%[\"\']}"
        if [[ -z "${!key+set}" ]]; then
            export "${key}=${value}"
        fi
    done < "$1"
}

# ---- the repository settings; GS_ROOT is the folder of slurm.env ----
gs_dir="${PWD}"
while [[ "${gs_dir}" != / && ! -f "${gs_dir}/slurm.env" ]]; do
    gs_dir="${gs_dir%/*}"
    gs_dir="${gs_dir:-/}"
done
source "${GS_HOME}/lib/cluster.sh"
if [[ -f "${gs_dir}/slurm.env" ]]; then
    export GS_ROOT="${GS_ROOT:-${gs_dir}}"
    gs_load_settings "${gs_dir}/slurm.env"
    # the project is named in slurm.env, else by the folder of slurm.env
    export GS_PROJECT="${GS_PROJECT:-${gs_dir##*/}}"
    gs_project_load
fi
unset gs_dir

# ---- the modules ----
for gs_module in args frame job env requeue submit table settings; do
    source "${GS_HOME}/lib/${gs_module}.sh"
done
unset gs_module

# -------------------------------------------
#! EOF
# -------------------------------------------
