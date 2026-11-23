#!/usr/bin/env bash
# Environment of a Python project on a cluster: modules, a virtualenv built once and rebuilt when pyproject.toml changes, CUDA library paths and
# thread counts.
#
# gs_venv ROOT VENV [EXTRAS] loads the modules of GS_MODULES (space separated, none by default), creates VENV, installs ROOT in editable mode
# with the pip EXTRAS, and sets GS_PYTHON. The build runs under a lock, so array tasks that start together build it once. A stamp holds the
# hash of the pyproject.toml it was installed from, and a failed install writes no stamp, so the next job tries again. Needs bash 4.1 and flock.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : env.sh
# -----------------------------------------------

gs_modules() {
    local module
    if ! command -v module >/dev/null 2>&1 || [[ -z "${GS_MODULES:-}" ]]; then
        return
    fi
    module reset >/dev/null 2>&1 || true
    for module in ${GS_MODULES}; do
        if ! module load "${module}"; then
            echo "gs_modules: WARNING: module ${module} not available" >&2
        fi
    done
}

# Pip-installed CUDA libraries first. "stubs" folders that some CUDA modules put on the path shadow the driver at run time and are dropped.
gs_cuda_paths() {
    local venv="$1"
    local entry
    local kept=""
    local nvidia
    local -a entries=()
    IFS=: read -ra entries <<< "${LD_LIBRARY_PATH:-}"
    for entry in ${entries[@]+"${entries[@]}"}; do
        if [[ -z "${entry}" || "$(basename "${entry}")" == stubs ]]; then
            continue
        fi
        kept="${kept:+${kept}:}${entry}"
    done
    nvidia=$(find "${venv}/lib" -type d -path "*/nvidia/*/lib" 2>/dev/null | paste -sd: - || true)
    export LD_LIBRARY_PATH="${nvidia}${nvidia:+${kept:+:}}${kept}"
}

gs_venv() {
    local root="$1"
    local venv="$2"
    local extras="${3:-}"
    local target="${root}${extras:+[${extras}]}"
    local stamp="${venv}/.installed-from"
    local wanted
    local lock
    if [[ ! -f "${root}/pyproject.toml" ]]; then
        gs_die "gs_venv: no pyproject.toml in ${root}"
    fi
    gs_modules

    mkdir -p "$(dirname "${venv}")"
    wanted="$(sha256sum "${root}/pyproject.toml" | cut -d' ' -f1)"
    exec {lock}>"${venv}.lock"
    flock "${lock}"
    if [[ ! -x "${venv}/bin/python" ]]; then
        echo "gs_venv: creating ${venv}" >&2
        python3 -m venv "${venv}"
        "${venv}/bin/python" -m pip install --upgrade pip
    fi
    if [[ "$(cat "${stamp}" 2>/dev/null)" != "${wanted}" ]]; then
        echo "gs_venv: installing ${target}" >&2
        if "${venv}/bin/python" -m pip install -e "${target}"; then
            echo "${wanted}" > "${stamp}"
        fi
    fi
    flock -u "${lock}"

    gs_cuda_paths "${venv}"
    export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
    export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
    export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
    export GS_PYTHON="${venv}/bin/python"
}

# The environment of a job: the virtualenv when GS_VENV is set, otherwise the modules.
gs_setup_env() {
    if [[ -n "${GS_VENV:-}" ]]; then
        gs_venv "${GS_ROOT:-${PWD}}" "${GS_VENV}" "${GS_EXTRAS:-}"
    else
        gs_modules
    fi
}

# -------------------------------------------
#! EOF
# -------------------------------------------
