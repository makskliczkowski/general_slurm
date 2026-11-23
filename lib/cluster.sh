#!/usr/bin/env bash
# Cluster settings chosen by host name, for clusters that share one home and one ~/.bashrc.
#
# The folder GS_CONFIG_DIR (default ~/.config/general_slurm) holds the host map "hosts", one "PATTERN CLUSTER" per line ("#" comments), and
# per cluster a file <cluster>.sh of "export NAME=value" lines, plus optional project files <project>/<cluster>.sh of the same form.
# gs_cluster_detect prints the cluster of the first pattern (a glob) that matches the short host name; the order of the lines decides when
# patterns overlap. gs_cluster_load exports GS_CLUSTER and sources the cluster file and every project file of that cluster. A host that
# matches no pattern gets one line on stderr and no settings; without a host map nothing is loaded and nothing printed. When GS_CLUSTER is
# already set, gs_cluster_load does nothing: a job inherits
# the settings of the shell it was submitted from, and the host name of a compute node does not choose them. ~/.bashrc sources this file
# alone (gs env install), so it needs no other part of the library.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : cluster.sh
# -----------------------------------------------

GS_CONFIG_DIR="${GS_CONFIG_DIR:-${XDG_CONFIG_HOME:-${HOME}/.config}/general_slurm}"

# The short host name; GS_HOSTNAME replaces it, for a check of the host map.
gs_hostname() {
    if [[ -n "${GS_HOSTNAME:-}" ]]; then
        echo "${GS_HOSTNAME}"
        return
    fi
    hostname -s 2>/dev/null || hostname
}

gs_cluster_detect() {
    local host
    local pattern
    local cluster
    host="$(gs_hostname)"
    if [[ ! -f "${GS_CONFIG_DIR}/hosts" ]]; then
        return
    fi
    while read -r pattern cluster _; do
        if [[ -z "${pattern}" || "${pattern}" == \#* ]]; then
            continue
        fi
        # the pattern is a glob, so it stays unquoted
        case "${host}" in
            ${pattern})
                echo "${cluster}"
                return
                ;;
        esac
    done < "${GS_CONFIG_DIR}/hosts"
}

gs_cluster_load() {
    local cluster
    local file
    # settings already inherited, or no host map set up: nothing to choose
    if [[ -n "${GS_CLUSTER:-}" || ! -f "${GS_CONFIG_DIR}/hosts" ]]; then
        return 0
    fi
    cluster="$(gs_cluster_detect)"
    if [[ -z "${cluster}" ]]; then
        echo "general_slurm: host $(gs_hostname) matches no pattern in ${GS_CONFIG_DIR}/hosts; no cluster settings loaded" >&2
        return 0
    fi
    export GS_CLUSTER="${cluster}"
    for file in "${GS_CONFIG_DIR}/${cluster}.sh" "${GS_CONFIG_DIR}"/*/"${cluster}.sh"; do
        if [[ -f "${file}" ]]; then
            source "${file}"
        fi
    done
    return 0
}

# -------------------------------------------
#! EOF
# -------------------------------------------
