#!/usr/bin/env bash
# Tables of runs: the row that one array task runs, and the packing of a table into array tasks.
#
# A table holds one entry per line; "#" starts a comment, blank lines are skipped. gs_row TABLE prints the row with index GS_TASK (from 0), so an
# array of n tasks runs a table of n rows, one row per task.
# gs_pack TABLE MAX_HOURS TARGET [WORD...] reads lines "CONFIG LABEL... RUNS HOURS [KEY=VALUE...] [request]", HOURS being the hours of the
# slowest run and KEY=VALUE job options of that line (cpus=8, mem=32G), and prints "CONFIG<tab>LABELS<tab>RUNS<tab>PER_TASK<tab>TASKS<tab>
# LIMIT<tab>OPTIONS" per selected line. Every WORD must equal a field of the line before RUNS;
# a "request" line runs only when its CONFIG is named. A run takes GS_MARGIN x HOURS (default 1.3). Runs share a task up to TARGET hours; a
# longer run gets a task of its own. LIMIT is the task's hours rounded up plus two, at most MAX_HOURS. A task that needs more than
# GS_MAX_RESTARTS restarts (default 10) gets a warning, since it would stop with runs left. A WORD that matches no line is an error.
# -----------------------------------------------
# Author            : Maks Kliczkowski
# File              : table.sh
# -----------------------------------------------

gs_row() {
    awk -v task="${GS_TASK:-${SLURM_ARRAY_TASK_ID:-0}}" '
        { sub(/#.*/, "") }
        NF == 0 { next }
        row == task { print; exit }
        { row++ }
    ' "$1"
}

gs_pack() {
    local table="$1"
    local max_hours="$2"
    local target="$3"
    shift 3
    awk -v words="$*" -v margin="${GS_MARGIN:-1.3}" -v max_hours="${max_hours}" -v target="${target}" -v max_restarts="${GS_MAX_RESTARTS:-10}" '
        BEGIN {
            n_words = split(words, word, " ")
            OFS = "\t"
        }

        { sub(/#.*/, "") }
        NF == 0 { next }

        {
            # the fields: CONFIG LABEL... RUNS HOURS, then KEY=VALUE options, then "request" or nothing
            request = ($NF == "request")
            last = NF - request
            options = ""
            while ($last ~ /=/) {
                options = $last (options == "" ? "" : " ") options
                last--
            }
            runs = $(last - 1)
            run_hours = margin * $last

            # selection: every word equals a field before RUNS; a request line needs its config named
            selected = !request
            for (i = 1; i <= n_words; i++) {
                hit = 0
                for (column = 1; column <= last - 2; column++) {
                    if ($column == word[i]) {
                        hit = 1
                        known[i] = 1
                        if (column == 1) {
                            selected = 1
                        }
                    }
                }
                if (!hit) {
                    next
                }
            }
            if (!selected) {
                next
            }

            # packing: runs that fit the target share a task, a longer run gets a task of its own
            per_task = 1
            if (run_hours <= target) {
                per_task = int(target / run_hours)
                if (per_task > runs) {
                    per_task = runs
                }
            }
            tasks = int((runs + per_task - 1) / per_task)
            limit = int(per_task * run_hours + 2.999)
            if (limit > max_hours) {
                limit = max_hours
            }

            # parts of one task: ceil(work / (limit - 1)), one hour of each part going to start-up and the stop margin
            parts = 1
            if (limit > 1) {
                parts = int(per_task * run_hours / (limit - 1))
                if (parts * (limit - 1) < per_task * run_hours) {
                    parts++
                }
            }
            labels = ""
            for (column = 2; column <= last - 2; column++) {
                labels = labels (column > 2 ? " " : "") $column
            }
            if (parts - 1 > max_restarts) {
                printf "warning: %s %s needs %d restarts per task, more than GS_MAX_RESTARTS=%d\n", $1, labels, parts - 1, max_restarts > "/dev/stderr"
            }
            print $1, labels, runs, per_task, tasks, limit, options
        }

        END {
            for (i = 1; i <= n_words; i++) {
                if (!known[i]) {
                    print "unknown selection: " word[i] > "/dev/stderr"
                    exit 2
                }
            }
        }
    ' "${table}"
}

# -------------------------------------------
#! EOF
# -------------------------------------------
