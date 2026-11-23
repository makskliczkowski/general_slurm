#!/usr/bin/env bash
# Declared arguments and settings of a script: each is declared once, gs_parse fills the variables, rejects unknown arguments and prints the
# help, and gs_print_settings lists every setting for a --print preview.
#
# Arguments: gs_positional VAR "help" (required, in order), gs_variadic VAR "help" [MIN] (at least MIN, default 1, after the positionals, into
# the array VAR),
# gs_option --name VAR DEFAULT "help" (--name VALUE or --name=VALUE),
# gs_list --name VAR "help" (repeatable, appends to the array VAR), gs_flag --name VAR "help" (VAR is 1 when given, else 0); then
# gs_parse "$@". Words after "--" go to the array GS_REST. Unknown options are an error, unless GS_UNKNOWN names an array that collects them.
# Settings: gs_env VAR DEFAULT "help" (optional), gs_need VAR "help" (required), gs_path VAR "help" (required folder, made absolute, created).
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : args.sh
# -----------------------------------------------

# The declarations, one entry per argument: kind (positional, option, list, flag), the option as typed, its variable, default and help.
GS_ARG_KIND=()
GS_ARG_NAME=()
GS_ARG_VAR=()
GS_ARG_DEFAULT=()
GS_ARG_HELP=()
# The settings listed by gs_print_settings, and the words after "--".
GS_SETTING_VAR=()
GS_SETTING_HELP=()
GS_REST=()

# Stop with a message on stderr and exit CODE (default 1).
gs_die() {
    echo "$(basename "$0"): $1" >&2
    exit "${2:-1}"
}

gs_declare() {
    GS_ARG_KIND+=("$1")
    GS_ARG_NAME+=("$2")
    GS_ARG_VAR+=("$3")
    GS_ARG_DEFAULT+=("$4")
    GS_ARG_HELP+=("$5")
}

gs_positional() {
    gs_declare positional "" "$1" "" "$2"
}

gs_variadic() {
    gs_declare variadic "" "$1" "${3:-1}" "$2"
    eval "$1=()"
}

gs_option() {
    gs_declare option "$1" "$2" "$3" "$4"
    printf -v "$2" '%s' "$3"
}

gs_list() {
    gs_declare list "$1" "$2" "" "$3"
    eval "$2=()"
}

gs_flag() {
    gs_declare flag "$1" "$2" 0 "$3"
    printf -v "$2" '%s' 0
}

# The usage line, built from the declarations.
gs_usage_line() {
    local i
    local line
    line="usage: $(basename "$0")"
    for i in "${!GS_ARG_KIND[@]}"; do
        case "${GS_ARG_KIND[i]}" in
            positional)
                line+=" ${GS_ARG_VAR[i]}"
                ;;
            variadic)
                if (( GS_ARG_DEFAULT[i] == 0 )); then
                    line+=" [${GS_ARG_VAR[i]}...]"
                else
                    line+=" ${GS_ARG_VAR[i]}..."
                fi
                ;;
            option)
                line+=" [${GS_ARG_NAME[i]} ${GS_ARG_VAR[i]}]"
                ;;
            list)
                line+=" [${GS_ARG_NAME[i]} ${GS_ARG_VAR[i]}]..."
                ;;
            flag)
                line+=" [${GS_ARG_NAME[i]}]"
                ;;
        esac
    done
    echo "${line}"
}

# The summary line of a script: its first comment line that is not the shebang or an #SBATCH line.
gs_summary() {
    awk 'NR > 1 && /^#/ && !/^#SBATCH/ { sub(/^# ?/, ""); print; exit }' "$1"
}

# The help: the summary line of the script, the usage line, then one line per argument with its default.
gs_help() {
    local i
    local name
    local default
    gs_summary "$0"
    gs_usage_line
    for i in "${!GS_ARG_KIND[@]}"; do
        name="${GS_ARG_NAME[i]:-${GS_ARG_VAR[i]}}"
        default=""
        if [[ -n "${GS_ARG_DEFAULT[i]}" && "${GS_ARG_KIND[i]}" == option ]]; then
            default=" (default ${GS_ARG_DEFAULT[i]})"
        fi
        printf '  %-22s %s%s\n' "${name}" "${GS_ARG_HELP[i]}" "${default}"
    done
}

# The index of the declared option that WORD names (--name or --name=VALUE), or nothing.
gs_find_option() {
    local i
    for i in "${!GS_ARG_KIND[@]}"; do
        if [[ -n "${GS_ARG_NAME[i]}" && ( "$1" == "${GS_ARG_NAME[i]}" || "$1" == "${GS_ARG_NAME[i]}="* ) ]]; then
            echo "${i}"
            return
        fi
    done
}

gs_parse() {
    local i
    local word
    local value
    local next=0
    local variadic=""
    local minimum=0
    local count
    local -a positions=()
    for i in "${!GS_ARG_KIND[@]}"; do
        if [[ "${GS_ARG_KIND[i]}" == positional ]]; then
            positions+=("${i}")
        fi
        if [[ "${GS_ARG_KIND[i]}" == variadic ]]; then
            variadic="${GS_ARG_VAR[i]}"
            minimum="${GS_ARG_DEFAULT[i]}"
        fi
    done

    while (( $# )); do
        word="$1"
        shift
        if [[ "${word}" == -h || "${word}" == --help ]]; then
            gs_help
            exit 0
        fi
        if [[ "${word}" == -- ]]; then
            GS_REST=("$@")
            break
        fi

        i="$(gs_find_option "${word}")"
        if [[ -n "${i}" ]]; then
            if [[ "${GS_ARG_KIND[i]}" == flag ]]; then
                printf -v "${GS_ARG_VAR[i]}" '%s' 1
                continue
            fi
            # the value follows "=" or is the next word
            if [[ "${word}" == *=* ]]; then
                value="${word#*=}"
            else
                if (( $# == 0 )); then
                    gs_die "${word} needs a value" 2
                fi
                value="$1"
                shift
            fi
            if [[ "${GS_ARG_KIND[i]}" == list ]]; then
                eval "${GS_ARG_VAR[i]}+=(\"\${value}\")"
            else
                printf -v "${GS_ARG_VAR[i]}" '%s' "${value}"
            fi
            continue
        fi

        if [[ "${word}" == -* ]]; then
            if [[ -z "${GS_UNKNOWN:-}" ]]; then
                gs_die "unknown argument ${word} ($(gs_usage_line))" 2
            fi
            eval "${GS_UNKNOWN}+=(\"\${word}\")"
            continue
        fi

        if (( next < ${#positions[@]} )); then
            printf -v "${GS_ARG_VAR[positions[next]]}" '%s' "${word}"
            next=$(( next + 1 ))
            continue
        fi
        if [[ -z "${variadic}" ]]; then
            gs_die "unexpected argument ${word} ($(gs_usage_line))" 2
        fi
        eval "${variadic}+=(\"\${word}\")"
    done

    if (( next < ${#positions[@]} )); then
        gs_die "missing ${GS_ARG_VAR[positions[next]]} ($(gs_usage_line))" 2
    fi
    if [[ -n "${variadic}" ]]; then
        eval "count=\${#${variadic}[@]}"
        if (( count < minimum )); then
            gs_die "missing ${variadic} ($(gs_usage_line))" 2
        fi
    fi
}

# ---- settings from the environment ----

gs_env() {
    if [[ -z "${!1:-}" ]]; then
        export "$1=$2"
    fi
    GS_SETTING_VAR+=("$1")
    GS_SETTING_HELP+=("$3")
}

gs_need() {
    if [[ -z "${!1:-}" ]]; then
        gs_die "set $1: $2" 2
    fi
    GS_SETTING_VAR+=("$1")
    GS_SETTING_HELP+=("$2")
}

gs_path() {
    gs_need "$1" "$2"
    mkdir -p "${!1}"
    export "$1=$(cd "${!1}" && pwd -P)"
}

# Every setting with its value and help, for --print.
gs_print_settings() {
    local i
    for i in "${!GS_SETTING_VAR[@]}"; do
        printf '  %-20s %-40s %s\n' "${GS_SETTING_VAR[i]}" "${!GS_SETTING_VAR[i]}" "${GS_SETTING_HELP[i]}"
    done
}

# -------------------------------------------
#! EOF
# -------------------------------------------
